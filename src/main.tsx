import React, {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {invoke,isTauri} from '@tauri-apps/api/core';
import './style.css';
import {Pairing} from './Pairing';

type Snapshot = {version:string, devices:string[], folders:string[]};
const languages = {
 it: {tabs:['Crea rete','Collega dispositivo','Dispositivi','Cartelle'], intro:['Configura il Mac mini come nodo principale.','Accedi alla tua rete Pairthing.'], pending:'Disponibile in una fase successiva.',demo:'Demo locale',lab:'Motore di laboratorio',empty:'Nessun elemento.',refresh:'Aggiorna',checking:'Verifica in corso', errors:{offline:'Motore irraggiungibile',auth:'Accesso negato',version:'Versione incompatibile',other:'Configurazione o risposta non valida'}},
 en: {tabs:['Create network','Connect device','Devices','Folders'], intro:['Set up your Mac mini as the primary node.','Sign in to your Pairthing network.'], pending:'Planned for a later release.',demo:'Local demo',lab:'Lab engine',empty:'No items.',refresh:'Refresh',checking:'Checking engine',errors:{offline:'Engine unreachable',auth:'Access denied',version:'Unsupported version',other:'Invalid configuration or response'}}
};
function App(){
 const [lang,setLang]=useState<'it'|'en'>(localStorage.getItem('language')==='en'?'en':'it');
 const [page,setPage]=useState(2),[data,setData]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(true);
 const t=languages[lang];
 async function refresh(){setBusy(true);setError('');try{setData(isTauri()?await invoke<Snapshot|null>('inspect_engine'):null)}catch(e){setData(null);setError(String(e))}finally{setBusy(false)}}
 useEffect(()=>{void refresh()},[]);
 useEffect(()=>{document.documentElement.lang=lang;localStorage.setItem('language',lang)},[lang]);
 const status=busy?t.checking:error?t.errors[error as keyof typeof t.errors]||t.errors.other:data?t.lab+' · '+data.version:t.demo;
 const items=busy||error?[]:page===2?(data?.devices??['Mac mini','Linux Mint']):(data?.folders??['Pairthing']);
 return <><header><strong>Pairthing</strong><select aria-label="Lingua / Language" value={lang} onChange={e=>setLang(e.target.value as 'it'|'en')}><option value="it">Italiano</option><option value="en">English</option></select></header><main className={isTauri()&&!data&&!error?'desktop':''}>{isTauri()&&!data&&!error?(busy?<p>{t.checking}</p>:<Pairing lang={lang}/>):<><nav>{t.tabs.map((v,i)=><button key={i} aria-current={page===i?'page':undefined} onClick={()=>setPage(i)}>{v}</button>)}</nav><section><p role="status">{status}</p><h1>{t.tabs[page]}</h1>{page<2?<><p>{t.intro[page]}</p><p>{t.pending}</p></>:<><ul>{items.map((v,i)=><li key={i}>{v||'—'}</li>)}</ul>{!items.length&&!busy&&!error&&<p>{t.empty}</p>}<button disabled={busy} onClick={refresh}>{t.refresh}</button></>}</section></>}</main></>
}
createRoot(document.getElementById('root')!).render(<App/>);
