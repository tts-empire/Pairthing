use serde::{Deserialize, Serialize};
use std::{env, net::SocketAddr, time::Duration};

#[derive(Deserialize)]
struct Status { #[serde(rename="myID")] id: String }
#[derive(Deserialize)]
struct Version { version: String }
#[derive(Deserialize)]
struct Device { name: String }
#[derive(Deserialize)]
struct Folder { label: String, id: String }
#[derive(Serialize)]
struct Snapshot { version: String, devices: Vec<String>, folders: Vec<String> }

struct SyncthingClient { address: SocketAddr, key: String, http: reqwest::Client }
impl SyncthingClient {
    fn new(address: &str, key: String) -> Result<Self,String> {
        let address: SocketAddr = address.parse().map_err(|_| "address")?;
        if !address.ip().is_loopback() || key.is_empty() { return Err("address".into()); }
        let http = reqwest::Client::builder().no_proxy().redirect(reqwest::redirect::Policy::none())
            .timeout(Duration::from_secs(4)).build().map_err(|_| "client")?;
        Ok(Self { address, key, http })
    }
    async fn get<T: serde::de::DeserializeOwned>(&self, path: &str) -> Result<T,String> {
        let response = self.http.get(format!("http://{}/rest/{}",self.address,path))
            .header("X-API-Key",&self.key).send().await.map_err(|_| "offline")?;
        match response.status().as_u16() {
            200 => response.json().await.map_err(|_| "schema".into()),
            401 | 403 => Err("auth".into()),
            _ => Err("engine".into())
        }
    }
    async fn snapshot(&self) -> Result<Snapshot,String> {
        let version: Version = self.get("system/version").await?;
        if !version.version.starts_with("v2.") { return Err("version".into()); }
        let status: Status = self.get("system/status").await?;
        if status.id.is_empty() { return Err("schema".into()); }
        let devices: Vec<Device> = self.get("config/devices").await?;
        let folders: Vec<Folder> = self.get("config/folders").await?;
        Ok(Snapshot {version:version.version, devices:devices.into_iter().map(|d|d.name).collect(),
            folders:folders.into_iter().map(|f|if f.label.is_empty(){f.id}else{f.label}).collect()})
    }
}
#[tauri::command]
async fn inspect_engine() -> Result<Option<Snapshot>,String> {
    let Ok(address) = env::var("PAIRTHING_LAB_ADDRESS") else { return Ok(None) };
    let client = SyncthingClient::new(&address,env::var("PAIRTHING_LAB_KEY").map_err(|_| "auth")?)?;
    client.snapshot().await.map(Some)
}
fn main() {
    tauri::Builder::default().invoke_handler(tauri::generate_handler![inspect_engine])
        .run(tauri::generate_context!()).expect("Pairthing desktop");
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn restrict_admin_to_loopback() {
        assert!(SyncthingClient::new("192.0.2.1:8384","test".into()).is_err());
        assert!(SyncthingClient::new("127.0.0.1:8384","".into()).is_err());
    }
}

#[cfg(test)]
mod integration {
    use super::*;
    use std::{io::{Read,Write}, net::TcpListener,thread};

    fn run_mock(replies: Vec<(&'static str,u16,&'static str)>) -> Result<Snapshot,String> {
        let listener=TcpListener::bind("127.0.0.1:0").unwrap();
        let client=SyncthingClient::new(&listener.local_addr().unwrap().to_string(),"fixture".into()).unwrap();
        let server=thread::spawn(move || {
            for (path,code,body) in replies {
                let (mut stream,_) = listener.accept().unwrap();
                let mut buffer=[0u8;4096];
                let count=stream.read(&mut buffer).unwrap();
                let request=String::from_utf8_lossy(&buffer[..count]);
                assert!(request.starts_with(&format!("GET /rest/{path} ")));
                assert!(request.to_ascii_lowercase().contains("x-api-key: fixture"));
                write!(stream,"HTTP/1.1 {code} Response\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len()).unwrap();
            }
        });
        let result=tauri::async_runtime::block_on(client.snapshot());
        server.join().unwrap();
        result
    }

    #[test]
    fn normal_response() {
        let data=run_mock(vec![("system/version",200,r#"{"version":"v2.1.6"}"#),
            ("system/status",200,r#"{"myID":"fixture-id"}"#),
            ("config/devices",200,r#"[{"name":"Mini"}]"#),
            ("config/folders",200,r#"[{"id":"f","label":"Docs"}]"#)]).unwrap();
        assert_eq!(data.devices,["Mini"]);assert_eq!(data.folders,["Docs"]);
    }
    #[test]
    fn denied(){assert_eq!(run_mock(vec![("system/version",403,"")]).err().as_deref(),Some("auth"));}
    #[test]
    fn incompatible(){assert_eq!(run_mock(vec![("system/version",200,r#"{"version":"v1.27"}"#)]).err().as_deref(),Some("version"));}
    #[test]
    fn offline(){
        let socket=TcpListener::bind("127.0.0.1:0").unwrap();
        let client=SyncthingClient::new(&socket.local_addr().unwrap().to_string(),"fixture".into()).unwrap();
        drop(socket);
        assert_eq!(tauri::async_runtime::block_on(client.snapshot()).err().as_deref(),Some("offline"));
    }
    #[test]
    #[ignore="requires scripts/lab.py"]
    fn lab_snapshot(){assert!(tauri::async_runtime::block_on(inspect_engine()).unwrap().is_some());}
}
