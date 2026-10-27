import React, { useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, Check, FileScan, ShieldAlert, Upload, X, Zap } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DOCUMENTS_BY_COUNTRY = {
  'India': ['Aadhaar', 'PAN', 'Passport', 'Birth Certificate', 'Driving Licence'],
  'USA': ['Passport', 'Visa', 'SSN', 'ID/Driving Licence', 'Health Insurance'],
  'UK': ['Passport', 'Visa/eVisa', 'National Insurance Number', 'ID', 'Health/NHS'],
  'Australia': ['Passport', 'Visa', 'TFN', 'Medicare/Insurance', 'Driving Licence'],
  'UAE': ['Passport', 'Residence Visa', 'Emirates ID', 'Health Insurance', 'Driving Licence'],
  'Singapore': ['Passport', 'Visa/Pass', 'FIN', 'ID', 'Health Insurance'],
  'Canada': ['Passport', 'Visa/Permit', 'SIN', 'Health Card', 'Driving Licence'],
};
const COUNTRIES = Object.keys(DOCUMENTS_BY_COUNTRY);
const COUNTRY_LABELS = {
  UK: 'UK (United Kingdom)',
  USA: 'USA (United States of America)',
  UAE: 'UAE (United Arab Emirates)',
};

function App() {
  const input = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [country, setCountry] = useState('India');
  const [documentType, setDocumentType] = useState(DOCUMENTS_BY_COUNTRY.India[0]);

  const choose = (selected) => {
    if (!selected) return;
    setFile(selected); setResult(null); setError('');
    setPreview(URL.createObjectURL(selected));
  };

  const useSpecimen = async () => {
    setError('');
    try {
      const response = await fetch(`${API}/api/specimen.png`);
      if (!response.ok) throw new Error('The bundled specimen could not be loaded.');
      const blob = await response.blob();
      choose(new File([blob], 'veriscan-specimen.png', { type: 'image/png' }));
    } catch (err) { setError(err.message); }
  };

  const scan = async () => {
    if (!file) return;
    setBusy(true); setError('');
    const body = new FormData(); body.append('file', file); body.append('country', country); body.append('document_category', documentType);
    try {
      const response = await fetch(`${API}/api/scan`, { method: 'POST', body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'The scan could not be completed.');
      setResult(data);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  return <div className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark"><Zap size={17} /></span><span>VERISCAN</span><small>VISIONARY6 / SIH26188</small></div><div className="status"><i /> LOCAL ANALYSIS MODE</div></header>
    <div className="demo-banner"><ShieldAlert size={17} /> Demo mode — do not upload real government ID documents. Use the provided SPECIMEN samples.</div>
    <main>
      <section className="intro"><div><p className="eyebrow">DOCUMENT SCREENING / 01</p><h1>See the signals<br /><em>behind the scan.</em></h1><p className="lede">An explainable screening workspace for human verifiers. Every score is a trail of evidence, not an authenticity verdict.</p></div><div className="intro-note"><span>PIPELINE STATUS</span><strong>6 stages ready</strong><div className="stage-line"><b /><b /><b /><b /><b /><b /></div></div></section>
      <section className="workbench">
        <div className="upload-panel">
          <div className="section-heading"><span>01 / INGEST</span><FileScan size={19} /></div>
          <label className="field-label" htmlFor="country">COUNTRY<select id="country" value={country} onChange={(event) => { const nextCountry = event.target.value; setCountry(nextCountry); setDocumentType(DOCUMENTS_BY_COUNTRY[nextCountry][0]); }}>{COUNTRIES.map((name) => <option key={name} value={name}>{COUNTRY_LABELS[name] || name}</option>)}</select></label>
          <label className="field-label" htmlFor="document-type">DOCUMENT<select id="document-type" value={documentType} onChange={(event) => setDocumentType(event.target.value)}>{DOCUMENTS_BY_COUNTRY[country].map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          <div className={`dropzone ${file ? 'has-file' : ''}`} onClick={() => input.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); choose(e.dataTransfer.files[0]); }}>
            <input ref={input} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => choose(e.target.files[0])} />
            {file ? <><img src={preview} alt="Selected document" /><div className="file-label"><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(0)} KB · click to replace</span></div></> : <><span className="upload-icon"><Upload size={22} /></span><strong>Drop a specimen here</strong><span>or browse JPEG / PNG files</span></>}
          </div>
          {error && <div className="error"><X size={17} />{error}</div>}
          <button className="primary" disabled={!file || busy} onClick={scan}>{busy ? 'ANALYZING...' : 'RUN SCREENING'} <ArrowUpRight size={18} /></button>
          <div className="specimen-link"><span>Need a safe sample?</span><button type="button" onClick={useSpecimen}>Load SPECIMEN document <ArrowUpRight size={13} /></button></div>
        </div>
        <div className="results-panel">
          {!result ? <div className="empty-state"><div className="orbit"><FileScan size={29} /></div><p>RESULTS WAITING</p><span>Upload a clearly labeled specimen image to map its evidence trail.</span></div> : <Results data={result} preview={preview} />}
        </div>
      </section>
      <section className="footer-strip"><div><span className="eyebrow">DESIGNED FOR REVIEW</span><strong>Keep the human in the loop.</strong></div><div className="limitations"><span>ELA is JPEG-specific</span><span>No fabricated accuracy claims</span><span>Moiré detection · coming soon</span></div></section>
    </main>
  </div>;
}

function Results({ data, preview }) {
  return <div className="result-content"><div className="result-top"><div><p className="eyebrow">SCREENING COMPLETE · {data.elapsed_ms} MS</p><h2>Evidence <em>ledger</em></h2><p className="document-kind">{data.document_category} · {data.country} · decision-support workflow</p></div><div className="score"><span>RISK SCORE</span><strong>{data.score}<small>/100</small></strong><em>{data.label}</em><p>Lower means fewer detected review signals. It is not proof of authenticity.</p></div></div><div className="result-grid"><div className="thumb-wrap"><img src={preview} alt="Uploaded document" /><span>ANALYZED INPUT</span></div><div className="checks">{data.checks.map((check) => <div className="check" key={check.name}><div className={`check-icon ${check.status}`} aria-label={check.status}>{check.status === 'pass' ? <Check size={16} /> : check.status === 'review' ? <ShieldAlert size={16} /> : '·'}</div><div><strong>{check.name}</strong><p>{check.detail}</p></div><b className={check.status}>{check.status}</b></div>)}</div></div><div className="text-extract"><span>OCR EXTRACT</span><code>{data.extracted_text || 'No text confidently extracted.'}</code></div><div className="rag-panel"><div className="rag-heading"><span>RETRIEVED GUIDANCE</span><small>LOCAL RAG · HUMAN REVIEW</small></div>{(data.retrieved_guidance || []).map((item) => <article className="rag-item" key={item.title}><strong>{item.title}</strong><span>{item.source} · match {item.match_score}</span><p>{item.guidance}</p></article>)}</div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
