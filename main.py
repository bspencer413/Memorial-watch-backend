<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>NYT Obituaries Tester</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    * { -webkit-tap-highlight-color: transparent; font-family: Georgia, 'Times New Roman', serif; }
    html, body { height: 100%; overflow-x: hidden; }
    .modal-drawer {
      position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
      background: #1a1a2e; border-radius: 20px 20px 0 0;
      border-top: 2px solid #c8a951;
      max-height: 88vh; overflow-y: auto;
      transform: translateY(0); transition: transform 0.3s ease;
      padding-bottom: max(1rem, env(safe-area-inset-bottom));
    }
    .modal-overlay { position: fixed; inset: 0; z-index: 99; background: rgba(0,0,0,0.65); }
  </style>
</head>
<body style="margin:0;padding:0;">
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect } = React;

const NYT_BASE    = 'https://nyt-obituaries-api.onrender.com';
const SSDI_BASE   = 'https://memorial-watch-backend-2.onrender.com';
const APP_VERSION = '0.4.11';
const BG_IMAGE    = 'url(background.jpg)';
const LOGO_SRC    = '3brains_one_mission.png';

const CONF_ORDER = { 'High':0, 'Likely':1, 'Possible':2, 'Related':3 };
const iClass     = "w-full px-4 py-3 rounded-xl text-lg bg-white/10 text-white placeholder-white/40 border-none outline-none focus:ring-2 focus:ring-yellow-600";
const cardClass  = "bg-black/40 rounded-2xl p-4 shadow-lg border border-yellow-900/30 backdrop-blur-sm";
const normName   = (n) => (n||'').toLowerCase().trim().replace(/\s+/g,' ');

const scoreResult = (result, searchFirst, searchMiddle, searchLast, searchBirthYear, searchSuffix) => {
  let score = 0;
  const rFirst  = (result.first_name  || '').toUpperCase();
  const rMiddle = (result.middle_name || '').toUpperCase();
  const rLast   = (result.last_name   || '').toUpperCase();
  const rSuffix = (result.suffix      || '').toUpperCase();
  const rDob    = (result.birth_date  || '');
  const sFirst  = (searchFirst  || '').toUpperCase();
  const sMiddle = (searchMiddle || '').toUpperCase().replace('.','');
  const sLast   = (searchLast   || '').toUpperCase();
  const sSuffix = (searchSuffix || '').toUpperCase();
  score += sFirst ? 30 : 50;
  if (sFirst) {
    if (rFirst === sFirst) score += 30;
    else if (rFirst.startsWith(sFirst) && rFirst.length <= sFirst.length + 1) score += 15;
  }
  if (sMiddle && rMiddle) {
    if (rMiddle === sMiddle || rMiddle.startsWith(sMiddle) || sMiddle.startsWith(rMiddle)) score += 30;
  }
  if (searchBirthYear && rDob && rDob.includes(searchBirthYear)) score += 15;
  if (sSuffix && rSuffix && rSuffix === sSuffix) score += 5;
  return score;
};

const confidenceLabel = (score) => {
  if (score >= 90) return 'Probable Match';
  if (score >= 60) return 'Possible Match';
  return 'Partial Match';
};

const SearchIcon   = () => <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>;
const HeartIcon    = () => <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>;
const MemoriesIcon = () => <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>;
const TrashIcon    = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>;
const EditIcon     = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>;
const PlusIcon     = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/></svg>;
const CheckIcon    = () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>;

const PageWrapper = ({ children, dark }) => (
  <div style={{ minHeight:'100dvh', width:'100%', position:'relative', paddingBottom:'5rem',
    backgroundColor:'#1a1a2e', backgroundImage:BG_IMAGE,
    backgroundSize:'cover', backgroundPosition:'center top',
    backgroundRepeat:'no-repeat', backgroundAttachment:'scroll' }}>
    <div style={{ position:'fixed', inset:0, zIndex:0, pointerEvents:'none',
      ...(dark
        ? { backdropFilter:'blur(8px)', WebkitBackdropFilter:'blur(8px)', backgroundColor:'rgba(10,4,0,0.55)' }
        : { background:'linear-gradient(to bottom, rgba(255,255,255,0.88) 0%, rgba(255,255,255,0.35) 10%, rgba(0,0,0,0.22) 30%, rgba(0,0,0,0.58) 100%)' }
      )
    }} />
    <div style={{ position:'relative', zIndex:10 }}>{children}</div>
  </div>
);

const ConfBadge = ({ conf }) => {
  const s = { 'High':'bg-green-800 text-green-200','Likely':'bg-blue-800 text-blue-200','Possible':'bg-yellow-800 text-yellow-200','Related':'bg-gray-700 text-gray-300' };
  return <span className={'inline-block text-xs font-bold tracking-widest uppercase px-2 py-0.5 rounded-md mb-2 '+(s[conf]||s['Related'])}>{conf}</span>;
};

const SuffixSelect = ({ value, onChange }) => (
  <select value={value} onChange={onChange}
    className={iClass+' appearance-none cursor-pointer'}
    style={{ backgroundImage:"url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23c8a951' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\")", backgroundRepeat:'no-repeat', backgroundPosition:'right 14px center', backgroundSize:'12px' }}>
    <option value="">Suffix: Jr., Sr., III — if applicable</option>
    <option value="Jr.">Jr.</option><option value="Sr.">Sr.</option>
    <option value="II">II</option><option value="III">III</option>
    <option value="IV">IV</option><option value="Esq.">Esq.</option>
  </select>
);

const Header = ({ apiVersion }) => (
  <div className="text-center" style={{ paddingTop:'16px' }}>
    <div className="flex justify-center items-center gap-2 mb-2">
      <span className="inline-block bg-yellow-600 text-black text-xs font-bold px-3 py-0.5 rounded tracking-widest">v{APP_VERSION}</span>
      <span className="inline-block border border-yellow-600 text-yellow-800 text-xs font-bold px-3 py-0.5 rounded tracking-widest">api {apiVersion}</span>
    </div>
    <img src={LOGO_SRC} alt="3Brains" className="h-12 w-auto mx-auto mb-1" />
    <p className="text-xs tracking-widest uppercase" style={{ color:'rgba(80,60,0,0.75)' }}>NYT Obituaries Tester</p>
  </div>
);

const BottomNav = ({ page, setPage, watchlistCount, memoriesCount, apiVersion }) => {
  const t = (name, label, Icon) => (
    <button onClick={() => setPage(name)}
      className={'flex flex-col items-center gap-0.5 px-1 py-1 relative '+(page===name?'text-yellow-500':'text-gray-400')}>
      <Icon /><span className="text-sm font-medium">{label}</span>
      {name==='watchlist' && watchlistCount>0 && <span className="absolute top-0 right-1 bg-green-600 text-white text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">{watchlistCount}</span>}
      {name==='memories'  && memoriesCount>0  && <span className="absolute top-0 right-1 bg-yellow-700 text-white text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">{memoriesCount}</span>}
    </button>
  );
  return (
    <div style={{ position:'fixed', bottom:0, left:0, right:0, backgroundColor:'rgba(10,0,0,0.95)', backdropFilter:'blur(8px)', borderTop:'2px solid #c8a951', padding:'0.5rem 1rem', paddingBottom:'max(0.5rem, env(safe-area-inset-bottom))' }}>
      <div className="flex justify-around max-w-sm mx-auto">
        {t('search','Search',SearchIcon)}
        {t('watchlist','Watchlist',HeartIcon)}
        {t('memories','Memories',MemoriesIcon)}
      </div>
      <p className="text-center text-gray-600 text-xs mt-1">app v{APP_VERSION} | api {apiVersion}</p>
    </div>
  );
};

const SsdiRecordDrawer = ({ record, onClose, onAddWatchlist, onSaveMemory, checkWatchlist, checkMemories }) => {
  if (!record) return null;
  const r = record;
  const alreadyWatching = checkWatchlist(r.name);
  const inMemories      = checkMemories(r.name);
  const byear    = r.birth_date ? parseInt((r.birth_date||'').split('/').pop()) : null;
  const isPassed = !!(r.death_date || (byear && byear < new Date().getFullYear() - 100));
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal-drawer">
        <div style={{ width:40, height:4, background:'rgba(255,255,255,0.2)', borderRadius:2, margin:'12px auto 0' }} />
        <div className="flex justify-between items-center px-4 pt-3 pb-2 border-b border-yellow-900/30">
          <h3 className="text-white font-bold text-base flex-1 pr-3">{r.name}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl font-bold leading-none">×</button>
        </div>
        <div className="p-4 space-y-3">
          <div className={'px-4 py-2 rounded-xl flex items-center gap-3 '+(isPassed?'bg-gray-800':'bg-green-800')}>
            <span className="text-white font-black tracking-widest text-base">{isPassed?'Passed Away':'No Death Record Found'}</span>
            {r.death_date && <span className="text-white/70 text-sm ml-auto">Died: {r.death_date}</span>}
          </div>
          <div className="bg-gray-800/60 rounded-xl p-3 border border-yellow-900/20">
            <p className="text-white font-bold text-lg mb-1">{r.name}</p>
            {r.middle_name && <p className="text-gray-400 text-sm">Middle: {r.middle_name}</p>}
            {r.birth_date  && <p className="text-gray-300 text-base">Born: {r.birth_date}</p>}
            {r.death_date  && <p className="text-gray-300 text-base">Died: {r.death_date}</p>}
            {r.state       && <p className="text-gray-400 text-sm">State: {r.state}</p>}
            <p className="text-gray-500 text-xs mt-2">Source: SSDI (records through 2014)</p>
          </div>
          {(() => {
            if (inMemories)      return <p className="text-yellow-400 text-base font-bold text-center">Already in Memories</p>;
            if (alreadyWatching) return <p className="text-green-400 text-base font-bold text-center">Already on Watchlist</p>;
            if (isPassed) return (
              <button onClick={() => { onSaveMemory({ _type:'memory_entry', saveTitle:r.name, name:r.name, headline:r.name, pub_date:r.death_date||'', byline:'', url:'', is_deceased:true, dod:r.death_date||null, death_year:r.death_date?(r.death_date.split('/').pop()||null):null, added:new Date().toLocaleDateString() }); onClose(); }}
                className="w-full py-4 bg-gray-700 hover:bg-gray-600 border border-gray-500 text-white rounded-xl font-bold text-xl flex items-center justify-center gap-2">
                <PlusIcon /> Save to Memories
              </button>
            );
            return (
              <button onClick={() => { onAddWatchlist(r.name); onClose(); }}
                className="w-full py-4 bg-yellow-600 hover:bg-yellow-700 text-black rounded-xl font-bold text-xl flex items-center justify-center gap-2">
                <PlusIcon /> Add to Watchlist
              </button>
            );
          })()}
          <button onClick={onClose} className="w-full py-3 bg-white/8 border border-white/15 text-white/70 rounded-xl text-base font-bold">Close</button>
        </div>
      </div>
    </>
  );
};

const SsdiResultsBlock = ({ results, searchFirst, searchMiddle, searchLast, searchBirthYear, searchSuffix, hasMore, onLoadMore, loadingMore, onSelect, ssdiPage, setSsdiPage }) => {
  if (!results || results.length === 0) return null;
  const tooMany = results.length >= 10 && !searchMiddle && !searchBirthYear;
  const visible = results.slice(0, ssdiPage * 10);
  const clientHasMore = results.length > visible.length;
  const ShowMoreBtn = () => (clientHasMore || hasMore) ? (
    <button onClick={() => { if (clientHasMore) setSsdiPage(p => p+1); else if (onLoadMore) onLoadMore(); }}
      disabled={loadingMore}
      className="w-full py-2.5 bg-gray-700 border border-yellow-800/50 text-white rounded-xl text-base font-bold mt-1 mb-1">
      {loadingMore ? 'Loading…' : 'Show 10 more ↓'}
    </button>
  ) : null;
  return (
    <div className="mb-3 p-3 bg-gray-800/60 rounded-xl border border-yellow-900/30">
      <p className="text-yellow-300 text-base font-bold mb-2">SSDI records — tap a name to view</p>
      {tooMany && <div className="mb-2 p-2 bg-yellow-900/30 border border-yellow-700/40 rounded-lg"><p className="text-yellow-300 text-xs">Many matches — add middle name, initial or birth year to narrow results.</p></div>}
      <ShowMoreBtn />
      {visible.map((r, i) => {
        const score = r._score !== undefined ? r._score : 50;
        const conf  = confidenceLabel(score);
        const confColor = conf==='Probable Match'?'text-green-400':conf==='Possible Match'?'text-yellow-400':'text-gray-400';
        return (
          <div key={i} onClick={() => onSelect(r)}
            className="mb-2 pb-2 border-b border-white/10 last:border-0 cursor-pointer hover:bg-white/5 rounded px-1 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-white text-base font-semibold underline decoration-dotted">{r.name}</p>
                {r.middle_name && <p className="text-gray-400 text-xs">Middle: {r.middle_name}</p>}
              </div>
              <span className={'text-xs font-bold ml-2 shrink-0 '+confColor}>{conf}</span>
            </div>
            {r.birth_date && <p className="text-gray-400 text-xs">Born: {r.birth_date}</p>}
            {r.death_date
              ? <p className="text-white text-xs font-semibold">Died: {r.death_date}</p>
              : <p className="text-gray-500 text-xs italic">No death record (SSDI through 2014)</p>}
          </div>
        );
      })}
      <ShowMoreBtn />
    </div>
  );
};

const RecordDrawer = ({ record, onClose, onSave, alreadySaved, isMemoryView }) => {
  const [moreOpen, setMoreOpen] = useState(false);
  useEffect(() => { setMoreOpen(false); }, [record]);
  if (!record) return null;
  const r = record;

  if (r._type === 'watchlist_entry' || r._type === 'memory_entry') {
    const isDeceased = !!(r.dod || r.death_year || r.is_deceased);
    const dodDisplay = r.dod || r.death_year || null;
    return (
      <>
        <div className="modal-overlay" onClick={onClose} />
        <div className="modal-drawer">
          <div style={{ width:40, height:4, background:'rgba(255,255,255,0.2)', borderRadius:2, margin:'12px auto 0' }} />
          <div className="flex justify-between items-center px-4 pt-3 pb-2 border-b border-yellow-900/30">
            <h3 className="text-white font-bold text-base flex-1 pr-3">{r.name||r.saveTitle}</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl font-bold leading-none">×</button>
          </div>
          <div className="p-4 space-y-3">
            <div className={'px-4 py-2 rounded-xl flex items-center gap-3 '+(isDeceased?'bg-gray-800':'bg-green-800')}>
              <span className="text-white font-black tracking-widest text-base">{isDeceased?'Passed Away':'Saved'}</span>
              {dodDisplay && <span className="text-white/70 text-sm ml-auto">Died: {dodDisplay}</span>}
            </div>
            <p className="text-white text-xl font-bold">{r.name||r.saveTitle}</p>
            {r.added && <p className="text-gray-400 text-sm">Added: {r.added}</p>}
            {!isMemoryView && !alreadySaved && (
              <button onClick={() => onSave(r)} className="w-full py-3 bg-green-800 hover:bg-green-700 text-white rounded-xl font-bold text-base">
                + Save to Memories
              </button>
            )}
            <button onClick={onClose} className="w-full py-3 bg-white/8 border border-white/15 text-white/70 rounded-xl text-base font-bold">Close</button>
          </div>
        </div>
      </>
    );
  }

  const conf    = r.confidence||'Related';
  const confBg  = conf==='High'?'bg-gray-800':conf==='Likely'?'bg-blue-900':conf==='Possible'?'bg-yellow-900':'bg-gray-700';
  const preview = r.abstract||r.snippet||r.body_text||'';
  const parts   = [];
  if (r.lead_paragraph && r.lead_paragraph.trim()) parts.push(r.lead_paragraph.trim());
  if (r.snippet && r.snippet.trim() && r.snippet.trim() !== (r.lead_paragraph||'').trim()) parts.push(r.snippet.trim());
  const fullText = parts.join('\n\n')||r.body_text||'';
  const hasMore  = fullText.trim() && fullText.replace(/\s+/g,' ').trim() !== preview.replace(/\s+/g,' ').trim() && fullText.length > preview.length + 60;

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal-drawer">
        <div style={{ width:40, height:4, background:'rgba(255,255,255,0.2)', borderRadius:2, margin:'12px auto 0' }} />
        <div className="flex justify-between items-center px-4 pt-3 pb-2 border-b border-yellow-900/30">
          <h3 className="text-white font-bold text-base flex-1 pr-3 leading-snug">{r.headline}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl font-bold leading-none">×</button>
        </div>
        <div className="p-4 space-y-3">
          <div className={'px-4 py-2 rounded-xl flex items-center gap-3 '+confBg}>
            <span className="text-white font-black tracking-widest text-base">{conf}</span>
            <span className="text-white/60 text-xs ml-auto">{r.news_desk?'NY Times · '+r.news_desk:'NY Times'}</span>
          </div>
          {r.photo_url && <img src={r.photo_url} alt="" className="w-full max-h-52 object-cover rounded-xl" onError={e=>e.target.style.display='none'} />}
          <h2 className="text-white text-xl font-bold leading-snug">{r.headline}</h2>
          <p className="text-gray-400 text-sm">{[r.pub_date,r.byline,r.section_name].filter(Boolean).join('  ·  ')}</p>
          {preview ? <p className="text-gray-200 text-lg leading-relaxed">{preview}</p> : null}
          {hasMore && !moreOpen && (
            <button onClick={() => setMoreOpen(true)} className="w-full py-3 bg-yellow-900/20 border border-yellow-700/30 text-yellow-300 rounded-xl text-base font-bold">More ▾</button>
          )}
          {moreOpen && <p className="text-gray-200 text-lg leading-relaxed whitespace-pre-line">{fullText}</p>}
          <div className="space-y-2 pt-2">
            <button onClick={() => onSave(r)} disabled={alreadySaved}
              className={'w-full py-3 rounded-xl font-bold text-base '+(alreadySaved?'bg-gray-700 text-gray-500 cursor-default':'bg-green-800 hover:bg-green-700 text-white')}>
              {alreadySaved ? '✓ In Memories' : '+ Save to Memories'}
            </button>
            {/* Copy Article Link — reserved for premium/NYT partnership */}
            <button onClick={onClose} className="w-full py-3 bg-white/8 border border-white/15 text-white/70 rounded-xl text-base font-bold">Back to Search</button>
          </div>
          <div className="p-2 bg-yellow-900/10 border border-yellow-800/20 rounded-xl">
            <p className="text-yellow-700 text-xs text-center">Content provided by The New York Times.</p>
          </div>
        </div>
      </div>
    </>
  );
};

const SearchPage = ({ onAddWatchlist, onSaveMemory, checkWatchlist, checkMemories, setApiVersion, setPage }) => {
  const [nw,           setNw]           = useState({ name:'', middle:'', suffix:'', birthYear:'' });
  const [searched,     setSearched]     = useState(false);
  const [searching,    setSearching]    = useState(false);
  const [statusMsg,    setStatusMsg]    = useState('');
  const [nytResults,   setNytResults]   = useState([]);
  const [ssdiResults,  setSsdiResults]  = useState([]);
  const [ssdiHasMore,  setSsdiHasMore]  = useState(false);
  const [ssdiOffset,   setSsdiOffset]   = useState(0);
  const [ssdiPage,     setSsdiPage]     = useState(1);
  const [ssdiLoading,  setSsdiLoading]  = useState(false);
  const [ssdiDrawer,   setSsdiDrawer]   = useState(null);
  const [articleDrawer,setArticleDrawer]= useState(null);
  const [debugRaw,     setDebugRaw]     = useState(null);
  const [debugOpen,    setDebugOpen]    = useState(false);

  const buildFullName = () => [nw.name, nw.suffix].filter(Boolean).join(' ').trim();

  const clearSearch = () => {
    setNw({ name:'', middle:'', suffix:'', birthYear:'' });
    setSearched(false); setNytResults([]); setSsdiResults([]);
    setSsdiHasMore(false); setSsdiOffset(0); setSsdiPage(1);
    setStatusMsg(''); setDebugRaw(null); setDebugOpen(false);
  };

  const doSearch = async () => {
    const name = (nw.name||'').trim();
    if (!name) return;
    setSearching(true); setSearched(false);
    setNytResults([]); setSsdiResults([]);
    setSsdiHasMore(false); setSsdiOffset(0); setSsdiPage(1);
    setStatusMsg('Searching NY Times…');

    const nameParts = name.split(/\s+/);
    const firstName = nameParts[0]||'';
    const lastName  = nameParts.slice(1).join(' ')||'';

    const nytParams = new URLSearchParams();
    nytParams.set('name',[name,nw.middle,nw.suffix].filter(Boolean).join(' '));
    if (firstName)    nytParams.set('first_name',    firstName);
    if (lastName)     nytParams.set('last_name',     lastName);
    if (nw.middle)    nytParams.set('middle_initial', nw.middle.trim().toUpperCase());
    if (nw.suffix)    nytParams.set('suffix',         nw.suffix);
    if (nw.birthYear) nytParams.set('birth_year',     nw.birthYear);

    const ssdiName   = firstName === lastName ? firstName : (firstName+' '+lastName).trim();
    const ssdiParams = new URLSearchParams({ name: ssdiName });
    if (nw.middle)    ssdiParams.append('middle_name', nw.middle.trim());
    if (nw.birthYear) ssdiParams.append('birth_year',  nw.birthYear);
    ssdiParams.append('offset','0');

    // NYT first — sequential to avoid BigQuery collision
    let nytData  = { results:[] };
    let ssdiData = { results:[], has_more:false };

    try {
      const nytRes = await fetch(NYT_BASE+'/nyt/search?'+nytParams.toString());
      nytData = await nytRes.json();
      if (nytData.version) setApiVersion(nytData.version);
    } catch(e) { console.log('NYT error:', e); }

    setStatusMsg('Searching SSDI records…');

    // SSDI via MW backend proxy — uses working BigQuery credentials
    try {
      const ssdiRes = await fetch(SSDI_BASE+'/ssdi/proxy?'+ssdiParams.toString());
      if (ssdiRes.ok) ssdiData = await ssdiRes.json();
    } catch(e) { console.log('SSDI error:', e); }

    const sortedNyt = (nytData.results||[]).slice().sort((a,b) => {
      const ao = CONF_ORDER[a.confidence]!==undefined?CONF_ORDER[a.confidence]:9;
      const bo = CONF_ORDER[b.confidence]!==undefined?CONF_ORDER[b.confidence]:9;
      return ao-bo;
    });

    const scoredSsdi = (ssdiData.results||[]).map(r =>
      Object.assign({}, r, { _score: scoreResult(r, firstName, nw.middle, lastName, nw.birthYear, nw.suffix) })
    ).sort((a,b) => b._score - a._score);

    if (scoredSsdi.length === 1) scoredSsdi[0]._score = 95;

    setNytResults(sortedNyt);
    setSsdiResults(scoredSsdi);
    setSsdiHasMore(ssdiData.has_more||false);
    setSsdiOffset(scoredSsdi.length);
    setStatusMsg('');
    setDebugRaw({
      nyt:  { url:NYT_BASE+'/nyt/search?'+nytParams.toString(),  results:sortedNyt.length },
      ssdi: { url:SSDI_BASE+'/ssdi/proxy?'+ssdiParams.toString(), results:scoredSsdi.length, has_more:ssdiData.has_more }
    });
    setSearching(false);
    setSearched(true);
  };

  const loadMoreSsdi = async () => {
    const name = (nw.name||'').trim();
    if (!name) return;
    setSsdiLoading(true);
    const nameParts = name.split(/\s+/);
    const firstName = nameParts[0]||'';
    const lastName  = nameParts.slice(1).join(' ')||'';
    const ssdiName  = firstName===lastName ? firstName : (firstName+' '+lastName).trim();
    try {
      const r = await fetch(SSDI_BASE+'/ssdi/proxy?name='+encodeURIComponent(ssdiName)+'&offset='+ssdiOffset);
      if (r.ok) {
        const data = await r.json();
        const newScored = (data.results||[]).map(rec =>
          Object.assign({}, rec, { _score: scoreResult(rec, firstName, nw.middle, lastName, nw.birthYear, nw.suffix) })
        );
        const combined = ssdiResults.concat(newScored);
        setSsdiResults(combined);
        setSsdiHasMore(data.has_more||false);
        setSsdiOffset(combined.length);
      }
    } catch(e) { console.log('loadMoreSsdi:', e); }
    setSsdiLoading(false);
  };

  const handleKey  = (e) => { if (e.key==='Enter') doSearch(); };
  const full       = buildFullName();
  const onWatchlist = checkWatchlist(full);
  const inMemories  = checkMemories(full);
  const hasAnyResults = nytResults.length > 0 || ssdiResults.length > 0;

  const watchlistStrip = () => {
    if (inMemories)  return <p className="text-yellow-400 text-base font-bold text-center py-2">"{full}" is saved in Memories</p>;
    if (onWatchlist) return <p className="text-green-400 text-base font-bold text-center py-2">"{full}" is on your Watchlist</p>;
    return (
      <button onClick={() => onAddWatchlist(full)}
        className="w-full py-3 bg-yellow-700/30 border border-yellow-600/40 text-yellow-300 rounded-xl font-bold text-base flex items-center justify-center gap-2">
        <PlusIcon /> Add "{full}" to Watchlist
      </button>
    );
  };

  return (
    <>
      <SsdiRecordDrawer
        record={ssdiDrawer} onClose={() => setSsdiDrawer(null)}
        onAddWatchlist={(name) => { onAddWatchlist(name); setSsdiDrawer(null); }}
        onSaveMemory={(r) => { onSaveMemory(r); setSsdiDrawer(null); }}
        checkWatchlist={checkWatchlist} checkMemories={checkMemories}
      />
      <RecordDrawer
        record={articleDrawer} onClose={() => setArticleDrawer(null)}
        onSave={(r) => onSaveMemory(r)}
        alreadySaved={articleDrawer ? checkMemories(articleDrawer.url||articleDrawer.headline||'') : false}
      />
      <div className="space-y-3 w-full px-3" style={{ paddingTop:'1rem' }}>
        <div className={cardClass}>
          <div className="mb-2 pb-2 border-b border-yellow-900/30 text-center">
            <p className="text-yellow-300 text-2xl font-bold italic whitespace-nowrap">Whatever happened to...</p>
            <p className="text-gray-300 text-base mt-0.5">Search NY Times &amp; SSDI records</p>
          </div>

          {!searched ? (
            <div className="space-y-3">
              <div className="relative">
                <input type="text" placeholder="First and Last Name *" value={nw.name}
                  onChange={e => setNw(p => Object.assign({},p,{name:e.target.value}))} onKeyPress={handleKey}
                  className={iClass+' pr-10'} autoCorrect="off" autoCapitalize="words" autoComplete="new-password" spellCheck="false"/>
                {nw.name && <button onClick={() => setNw(p => Object.assign({},p,{name:''}))} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white text-xl font-bold" type="button">×</button>}
              </div>
              <div className="relative">
                <input type="text" placeholder="Middle Name or Initial — Helpful" value={nw.middle}
                  onChange={e => setNw(p => Object.assign({},p,{middle:e.target.value}))} onKeyPress={handleKey}
                  className={iClass+' pr-10'} autoCorrect="off" autoComplete="new-password" spellCheck="false"/>
                {nw.middle && <button onClick={() => setNw(p => Object.assign({},p,{middle:''}))} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white text-xl font-bold" type="button">×</button>}
              </div>
              <SuffixSelect value={nw.suffix} onChange={e => setNw(p => Object.assign({},p,{suffix:e.target.value}))} />
              <div className="relative">
                <input type="tel" placeholder="Birth Year — Helpful" value={nw.birthYear}
                  onChange={e => setNw(p => Object.assign({},p,{birthYear:e.target.value.replace(/\D/g,'').slice(0,4)}))} onKeyPress={handleKey}
                  className={iClass+' pr-10'} maxLength={4} autoComplete="new-password"/>
                {nw.birthYear && <button onClick={() => setNw(p => Object.assign({},p,{birthYear:''}))} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white text-xl font-bold" type="button">×</button>}
              </div>
              <button onClick={doSearch} disabled={searching}
                className="w-full py-4 bg-yellow-600 hover:bg-yellow-700 text-black rounded-xl font-bold text-xl flex items-center justify-center gap-2 disabled:opacity-50">
                <SearchIcon /> {searching ? (statusMsg||'Searching…') : 'Search'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {nytResults.length > 0 && (
                <>
                  <p className="text-yellow-400/80 text-sm font-bold">NY Times — {nytResults.length} result(s)</p>
                  {nytResults.map((r,i) => (
                    <div key={i} onClick={() => setArticleDrawer(r)}
                      className="bg-black/50 border border-yellow-900/25 border-l-4 border-l-yellow-600 rounded-xl p-4 cursor-pointer hover:bg-black/70 transition-colors backdrop-blur-sm">
                      <ConfBadge conf={r.confidence||'Related'} />
                      <h3 className="text-white text-lg font-semibold leading-snug mb-1">{r.headline}</h3>
                      <p className="text-gray-400 text-sm mb-1">{r.pub_date}&nbsp;·&nbsp;{r.byline||'NY Times'}&nbsp;·&nbsp;{r.section_name||''}</p>
                      {(r.snippet||r.body_text) && <p className="text-gray-300 text-base leading-relaxed">{r.snippet||r.body_text}</p>}
                    </div>
                  ))}
                </>
              )}

              {ssdiResults.length > 0 && (
                <>
                  <p className="text-yellow-400/80 text-sm font-bold mt-2">SSDI Records</p>
                  <SsdiResultsBlock
                    results={ssdiResults}
                    searchFirst={(nw.name||'').split(/\s+/)[0]||''}
                    searchMiddle={nw.middle}
                    searchLast={(nw.name||'').split(/\s+/).slice(-1)[0]||''}
                    searchBirthYear={nw.birthYear}
                    searchSuffix={nw.suffix}
                    hasMore={ssdiHasMore} onLoadMore={loadMoreSsdi}
                    loadingMore={ssdiLoading} onSelect={(r) => setSsdiDrawer(r)}
                    ssdiPage={ssdiPage} setSsdiPage={setSsdiPage}
                  />
                </>
              )}

              {!hasAnyResults && (
                <div className="rounded-2xl overflow-hidden border border-yellow-800/40">
                  <div className="px-4 py-2 bg-gray-800">
                    <span className="text-white font-black tracking-widest text-base">Name Not Found</span>
                  </div>
                  <div className="bg-gray-900/70 p-4 space-y-3">
                    <p className="text-white text-xl font-bold">{full}</p>
                    <p className="text-gray-300 text-lg leading-relaxed">No records found. Try adding a middle initial, suffix, or birth year and search again.</p>
                    {onWatchlist
                      ? <p className="text-green-400 text-base font-bold text-center">Already on your Watchlist</p>
                      : inMemories
                        ? <p className="text-yellow-400 text-base font-bold text-center">Already saved in Memories</p>
                        : <>
                            <button onClick={() => { onAddWatchlist(full); setPage('watchlist'); }}
                              className="w-full py-4 bg-yellow-600 hover:bg-yellow-700 text-black rounded-xl font-bold text-xl flex items-center justify-center gap-2">
                              <PlusIcon /> Add "{full}" to Watchlist
                            </button>
                            <button onClick={() => { onSaveMemory({ _type:'memory_entry', saveTitle:full, name:full, headline:full, pub_date:'', byline:'', url:'', is_deceased:false, added:new Date().toLocaleDateString() }); setPage('memories'); }}
                              className="w-full py-3 bg-gray-700/60 border border-gray-500/40 text-gray-200 rounded-xl text-lg flex items-center justify-center gap-2">
                              <PlusIcon /> Save to Memories instead
                            </button>
                          </>
                    }
                  </div>
                </div>
              )}

              {hasAnyResults && <div className="pt-1">{watchlistStrip()}</div>}

              <div className="flex gap-2">
                <button onClick={() => { setSearched(false); setNytResults([]); setSsdiResults([]); setDebugRaw(null); setDebugOpen(false); setStatusMsg(''); }}
                  className="flex-1 py-2.5 bg-white/10 border border-white/20 text-white/70 rounded-xl text-base flex items-center justify-center gap-1">
                  <EditIcon /> Edit Name
                </button>
                <button onClick={clearSearch} className="flex-1 py-2.5 bg-white/10 border border-white/20 text-white/70 rounded-xl text-base text-center">New Search</button>
              </div>

              {debugRaw && (
                <div>
                  <button onClick={() => setDebugOpen(!debugOpen)}
                    className="w-full flex justify-between items-center px-3 py-2 bg-black/40 border border-white/8 text-white/30 rounded-t-lg text-xs uppercase tracking-widest">
                    <span>{debugOpen?'▼':'▶'} Raw API Response</span>
                    <span>{debugOpen?'HIDE':'SHOW'}</span>
                  </button>
                  {debugOpen && (
                    <pre className="bg-black/90 border border-white/8 border-t-0 rounded-b-lg p-3 text-xs text-green-400 overflow-auto max-h-56 whitespace-pre-wrap break-all">
                      {JSON.stringify(debugRaw,null,2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

const WatchlistPage = ({ watchlist, onRemove, onCopyToMemories, checkMemories }) => {
  const [drawer, setDrawer] = useState(null);
  return (
    <>
      <RecordDrawer record={drawer} onClose={() => setDrawer(null)}
        onSave={(r) => onCopyToMemories(r)}
        alreadySaved={drawer ? checkMemories(drawer.name||'') : false} />
      <div className="space-y-3 w-full px-3" style={{ paddingTop:'1rem' }}>
        <div className={cardClass}>
          <div className="mb-2 pb-2 border-b border-yellow-900/30 text-center">
            <h2 className="text-3xl font-black text-white tracking-wide">Watchlist</h2>
            <p className="text-gray-300 text-base mt-1">Tap a name to view — we'll notify you when they pass</p>
          </div>
          {watchlist.length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-gray-300 text-base leading-relaxed mb-2">No one on your watchlist yet.</p>
              <p className="text-yellow-400 text-base font-medium">Use Search to find and add people.</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xl font-bold text-white text-center mb-1">Your Watchlist ({watchlist.length})</p>
              {watchlist.map((w,i) => (
                <div key={i} className="p-4 rounded-xl border bg-gray-800/50 border-yellow-900/20 flex items-center justify-between">
                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setDrawer(Object.assign({},w,{_type:'watchlist_entry'}))}>
                    <p className="font-semibold text-xl text-white underline decoration-dotted truncate">{w.name}</p>
                    <div className="flex items-center gap-1 mt-1"><CheckIcon /><span className="text-base text-green-400">Following</span></div>
                    <p className="text-gray-500 text-xs mt-0.5">Added {w.added}</p>
                  </div>
                  <div className="flex gap-2 ml-2 shrink-0">
                    <button onClick={() => onCopyToMemories(w)}
                      className="px-3 py-1.5 bg-gray-700/60 border border-gray-500/40 text-gray-200 rounded-lg text-sm font-bold whitespace-nowrap">
                      + Memories
                    </button>
                    <button onClick={() => onRemove(w.name)} className="p-2 text-red-500 hover:bg-red-900/30 rounded-lg"><TrashIcon /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

const MemoriesPage = ({ memories, onDelete }) => {
  const [drawer, setDrawer] = useState(null);
  return (
    <>
      <RecordDrawer record={drawer} onClose={() => setDrawer(null)} onSave={() => {}} alreadySaved={true} isMemoryView={true} />
      <div className="space-y-3 w-full px-3" style={{ paddingTop:'1rem' }}>
        <div className={cardClass}>
          <div className="mb-2 pb-2 border-b border-yellow-900/30 text-center">
            <h2 className="text-3xl font-black text-white tracking-wide">Memories</h2>
            <p className="text-gray-300 text-base mt-1">People you have found who have passed</p>
          </div>
          {memories.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-300 text-lg leading-relaxed">Save obituaries here for future reference by tapping Save to Memories in any result.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xl font-bold text-white text-center mb-1">Saved Memories ({memories.length})</p>
              {memories.map((m,i) => {
                const isDeceased  = !!(m.dod||m.death_year||m.is_deceased||m.pub_date);
                const displayName = m.saveTitle||m.name||m.headline||'';
                const dodDisplay  = m.dod||m.death_year||(m.pub_date?m.pub_date.slice(0,4):null);
                const statusText  = isDeceased?('Passed Away'+(dodDisplay?' — '+dodDisplay:'')):'Saved';
                return (
                  <div key={i} className="p-4 bg-gray-900/70 rounded-xl border border-gray-600/50 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className={'font-semibold text-xl truncate '+(isDeceased?'text-gray-300 line-through':'text-white')}>{displayName}</h3>
                      <span className="text-base text-gray-400 font-bold">{statusText}</span>
                    </div>
                    <div className="flex gap-2 ml-2 shrink-0">
                      <button onClick={() => setDrawer(Object.assign({},m,{_type:'memory_entry',name:displayName}))}
                        className="px-3 py-1.5 bg-yellow-700/40 border border-yellow-600/40 text-white rounded-lg text-sm font-bold">View</button>
                      <button onClick={() => onDelete(i)} className="p-2 text-red-500 hover:bg-red-900/30 rounded-lg"><TrashIcon /></button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

function App() {
  const [page,       setPage]       = useState('search');
  const [apiVersion, setApiVersion] = useState('—');
  const [watchlist,  setWatchlist]  = useState(() => JSON.parse(localStorage.getItem('nyt_watchlist')||'[]'));
  const [memories,   setMemories]   = useState(() => JSON.parse(localStorage.getItem('nyt_memories') ||'[]'));

  useEffect(() => {
    fetch(NYT_BASE+'/')
      .then(r => r.json())
      .then(d => { if (d.version) setApiVersion(d.version); })
      .catch(() => {});
  }, []);

  const saveWatchlist = (list) => { setWatchlist(list); localStorage.setItem('nyt_watchlist',JSON.stringify(list)); };
  const saveMemories  = (list) => { setMemories(list);  localStorage.setItem('nyt_memories', JSON.stringify(list)); };

  const checkWatchlist = (name) => {
    if (!name) return false;
    return watchlist.some(w => normName(w.name) === normName(name));
  };

  const checkMemories = (key) => {
    if (!key) return false;
    const k = normName(key);
    return memories.some(m =>
      normName(m.url||'')===k || normName(m.saveTitle||'')===k ||
      normName(m.name||'')===k || normName(m.headline||'')===k
    );
  };

  const addToWatchlist = (name) => {
    if (checkWatchlist(name)) return;
    saveWatchlist(watchlist.concat([{ name, added:new Date().toLocaleDateString() }]));
  };

  const saveToMemory = (r) => {
    const key = r.url||r.saveTitle||r.name||r.headline||'';
    if (checkMemories(key)) return;
    saveMemories(memories.concat([r]));
  };

  const copyWatchlistToMemories = (w) => {
    saveToMemory(Object.assign({},w,{
      _type:'memory_entry', saveTitle:w.name, name:w.name,
      headline:w.name, pub_date:'', byline:'', url:'',
      is_deceased:false, added:new Date().toLocaleDateString()
    }));
  };

  return (
    <PageWrapper dark={page!=='search'}>
      <Header apiVersion={apiVersion} />
      {page==='search' && (
        <SearchPage
          onAddWatchlist={addToWatchlist} onSaveMemory={saveToMemory}
          checkWatchlist={checkWatchlist} checkMemories={checkMemories}
          setApiVersion={setApiVersion} setPage={setPage}
        />
      )}
      {page==='watchlist' && (
        <WatchlistPage
          watchlist={watchlist}
          onRemove={(name) => saveWatchlist(watchlist.filter(w => w.name!==name))}
          onCopyToMemories={copyWatchlistToMemories}
          checkMemories={checkMemories}
        />
      )}
      {page==='memories' && (
        <MemoriesPage
          memories={memories}
          onDelete={(i) => saveMemories(memories.filter((_,j) => j!==i))}
        />
      )}
      <BottomNav
        page={page} setPage={setPage}
        watchlistCount={watchlist.length} memoriesCount={memories.length}
        apiVersion={apiVersion}
      />
    </PageWrapper>
  );
}

ReactDOM.render(React.createElement(App), document.getElementById('root'));
</script>
</body>
</html>
