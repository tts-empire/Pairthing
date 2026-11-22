use serde_json::{json, Value};
use std::{
    env, fs,
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
};
use tauri::{AppHandle, Manager, State};

#[derive(Default)]
pub struct Desktop {
    worker: Mutex<Option<Child>>,
    snapshot: Arc<Mutex<Value>>,
}

fn profile(app: &AppHandle) -> Result<PathBuf, String> {
    let root = app.path().app_local_data_dir().map_err(|_| "profile")?;
    fs::create_dir_all(&root).map_err(|_| "profile")?;
    Ok(root.join("profile"))
}

#[tauri::command]
pub fn desktop_state(app: AppHandle, state: State<Desktop>) -> Result<Value, String> {
    let mut worker = state.worker.lock().map_err(|_| "worker")?;
    if worker.is_none() {
        let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
        let linux = cfg!(target_os = "linux");
        let runtime = repo.join(if linux { ".tools/linux-trial/venv" } else { ".tools/pair-env" });
        let resources = if linux {
            std::env::current_exe().map_err(|_| "runtime")?.parent().ok_or("runtime")?.to_owned()
        } else {
            app.path().resource_dir().map_err(|_| "runtime")?
        };
        let packaged = resources.join("runtime/pairthing-controller/pairthing-controller");
        let mut command = if packaged.is_file() {
            let mut cmd = Command::new(packaged);
            cmd.env("PAIRTHING_ENGINE", resources.join("runtime/syncthing"));
            cmd
        } else {
            let mut cmd = Command::new(runtime.join("bin/python"));
            cmd.arg("-u").arg(repo.join("scripts/pairing/desktop.py"));
            if linux {
                cmd.env("PAIRTHING_ENGINE", repo.join(".tools/linux-trial/syncthing-2.1.7"));
            }
            cmd
        };
        command.arg(profile(&app)?).env("AUTOBAHN_USE_NVX", "0");
        let mut child = command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null())
            .spawn().map_err(|_| "runtime")?;
        let stdout = child.stdout.take().ok_or("worker")?;
        let target = Arc::clone(&state.snapshot);
        *target.lock().map_err(|_| "worker")? = json!({"stage":"loading"});
        thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if let Ok(event) = serde_json::from_str::<Value>(&line) {
                    if event["stage"].is_string() {
                        *target.lock().unwrap() = event;
                    }
                }
            }
            *target.lock().unwrap() = json!({"stage":"unavailable"});
        });
        *worker = Some(child);
    }
    Ok(state.snapshot.lock().map_err(|_| "worker")?.clone())
}

#[tauri::command]
pub fn desktop_action(app: AppHandle, state: State<Desktop>, action: String, code: Option<String>) -> Result<(), String> {
    if action == "open" {
        let folder = profile(&app)?.join("Files");
        if !folder.is_dir() { return Err("folder".into()); }
        return Command::new(if cfg!(target_os="macos") { "open" } else { "xdg-open" })
            .arg(folder).spawn().map(|_| ()).map_err(|_| "folder".into());
    }
    if !matches!(action.as_str(), "invite" | "join" | "approve" | "cancel" | "retry") {
        return Err("action".into());
    }
    let code = code.unwrap_or_default();
    if action == "join" && (code.len() > 128 || code.is_empty() ||
        !code.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-')) {
        return Err("code".into());
    }
    let mut worker = state.worker.lock().map_err(|_| "worker")?;
    let input = worker.as_mut().and_then(|child| child.stdin.as_mut()).ok_or("worker")?;
    writeln!(input, "{}", json!({"action": action, "code":code})).map_err(|_| "worker".into())
}
