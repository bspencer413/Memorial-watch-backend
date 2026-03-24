<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="theme-color" content="#dc2626">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <title>Dead or Alive -- DORA</title>
  <meta name="description" content="DORA -- Dead or Alive. The only app with a death watchlist. Add anyone to your watchlist and get notified the moment they pass away. Search celebrities, friends, colleagues and find out instantly if they are dead or alive.">
  <meta name="keywords" content="dead or alive, death watchlist, obituary alert, death notification, passed away notification, Legacy obituary, Wikipedia deaths, deceased alert">
  <meta name="robots" content="index, follow">
  <meta name="author" content="DORA">
  <link rel="canonical" href="https://dora.watch">
  <meta property="og:title" content="DORA -- Dead or Alive. Know Instantly.">
  <meta property="og:description" content="The only death watchlist app. Add friends, family, colleagues or celebrities -- get notified the moment they pass away.">
  <meta property="og:url" content="https://dora.watch">
  <meta property="og:type" content="website">
  <meta property="og:image" content="https://raw.githubusercontent.com/bspencer413/DORA/main/wanted.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="DORA -- Dead or Alive Death Watchlist">
  <meta name="twitter:description" content="Add anyone to your death watchlist. Get notified instantly when they pass away.">
  <meta name="twitter:image" content="https://raw.githubusercontent.com/bspencer413/DORA/main/wanted.png">
  <link rel="manifest" href="data:application/json;base64,eyJuYW1lIjoiRGVhZCBvciBBbGl2ZSIsInNob3J0X25hbWUiOiJET1JBIiwic3RhcnRfdXJsIjoiLyIsImRpc3BsYXkiOiJzdGFuZGFsb25lIiwiYmFja2dyb3VuZF9jb2xvciI6IiM3ZjFkMWQiLCJ0aGVtZV9jb2xvciI6IiNkYzI2MjYiLCJpY29ucyI6W3sic3JjIjoiaHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2JzcGVuY2VyNDEzL0RPUkEvbWFpbi9kb3JhX2ljb24ucG5nIiwic2l6ZXMiOiI1MTJ4NTEyIiwidHlwZSI6ImltYWdlL3BuZyJ9XX0=">
  <link rel="apple-touch-icon" href="https://raw.githubusercontent.com/bspencer413/DORA/main/dora_icon.png">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    * { -webkit-tap-highlight-color: transparent; font-family: Georgia, 'Times New Roman', serif; }
    html, body { height: 100%; overflow-x: hidden; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .tap-pulse { animation: pulse 1.8s ease-in-out infinite; }
    .modal-drawer {
      position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
      background: #1a1a2e; border-radius: 20px 20px 0 0;
      border-top: 1px solid #7f1d1d;
      max-height: 85vh; overflow-y: auto;
      transform: translateY(0);
      transition: transform 0.3s ease;
      padding-bottom: max(1rem, env(safe-area-inset-bottom));
    }
    .modal-overlay { position: fixed; inset: 0; z-index: 99; background: rgba(0,0,0,0.6); }
  </style>
</head>
<body style="margin:0;padding:0;">
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect } = React;

const API_BASE = 'https://memorial-watch-backend-2.onrender.com';
const WANTED_BG = 'https://raw.githubusercontent.com/bspencer413/DORA/main/wanted.png';
const BILL_PHOTO = 'https://raw.githubusercontent.com/Bspencer413/Memorial-watch/main/Bill.jpeg';
const APP_VERSION = '1.2.8';

const isPhone = window.innerWidth < 500;
const isTablet = window.innerWidth >= 500 && window.innerWidth < 1024;
const PT = isPhone ? '38vh' : isTablet ? '48vh' : '44vh';
const TAP_TOP = isPhone ? '82%' : '84%';

const toTitleCase = (str) => {
  if (!str) return str;
  return str
    .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase())
    .replace(/'\w/g, (txt) => txt.toUpperCase());
};

// Strip middle names/initials for Wikipedia lookup only
const normalizeForWiki = (name) => {
  if (!name) return name;
  name = name.trim();
  if (name.indexOf(',') > -1) {
    const parts = name.split(',');
    name = parts[1].trim() + ' ' + parts[0].trim();
  }
  // Strip middle initials: single letters with or without period (S, S., Sr., Jr. kept)
  const words = name.split(/\s+/).filter(w => {
    const stripped = w.replace(/\./g, '');
    // Keep if more than 1 real letter (so "Jr" "Sr" "III" "IV" are kept)
    // Strip if single letter or single letter + period (middle initials)
    return stripped.length > 1;
  });
  if (words.length >= 3) return toTitleCase(words[0] + ' ' + words[words.length - 1]);
  return toTitleCase(words.join(' '));
};

// Add period after bare single-letter middle initials
// "Robert S Mueller" -> "Robert S. Mueller"
const addInitialPeriods = (name) => {
  if (!name) return name;
  return name.trim().split(/\s+/).map((word, i, arr) => {
    if (word.length === 1 && /[A-Za-z]/.test(word) && i > 0 && i < arr.length - 1) {
      return word + '.';
    }
    return word;
  }).join(' ');
};

const HomeIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);
const HeartIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
  </svg>
);
const SearchIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);
const InfoIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);
const BellIcon = ({ red }) => (
  <svg className="w-7 h-7" fill="none" stroke={red ? '#dc2626' : 'currentColor'} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);
const PlusIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);
const TrashIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);
const EditIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
  </svg>
);
const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);
const EyeIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
);
const EyeOffIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
  </svg>
);

const ClearableInput = ({ value, onChange, onBlur, onKeyPress, placeholder, type='text', maxLength, inputClass }) => (
  <div className="relative">
    <input type={type} placeholder={placeholder} value={value} onChange={onChange} onBlur={onBlur} onKeyPress={onKeyPress} maxLength={maxLength} className={inputClass + ' pr-10'} />
    {value && value.length > 0 && (
      <button onClick={() => onChange({ target: { value: '' } })} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white text-lg font-bold leading-none" type="button">X</button>
    )}
  </div>
);

const CardPageHeader = ({ title, subtitle, onHome }) => (
  <div className="mb-3 pb-2 border-b border-red-900/30">
    <div className="flex items-center justify-between">
      <div className="w-10" />
      <h2 className="text-xl font-black text-white tracking-wide text-center flex-1">{title}</h2>
      <button onClick={onHome} className="flex flex-col items-center text-white hover:text-red-400 transition-colors w-10">
        <HomeIcon />
        <span className="text-xs">Home</span>
      </button>
    </div>
    {subtitle && <p className="text-gray-300 text-xs mt-1 text-center">{subtitle}</p>}
  </div>
);

const POSTER_STYLE = {
  backgroundColor: '#2c1a0e',
  backgroundImage: 'url(' + WANTED_BG + ')',
  backgroundSize: 'contain',
  backgroundPosition: 'center top',
  backgroundRepeat: 'no-repeat',
  backgroundAttachment: 'fixed',
};

const PageWrapper = ({ children }) => (
  <div style={{ minHeight: '100dvh', width: '100%', position: 'relative', paddingBottom: '5rem', ...POSTER_STYLE }}>
    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.22)' }} />
    <div style={{ position: 'relative', zIndex: 10 }}>{children}</div>
  </div>
);

function isDeceasedCheck(extract, description, deathDate, type) {
  if (type === 'disambiguation') return false;
  if (deathDate) return true;
  const firstSentence = extract ? extract.split('.')[0] : '';
  const hasDeathInBrackets = /\(\d{4}\s*[-\u2013\u2014]+\s*\d{4}\)/.test(firstSentence);
  const hasYearsInDescription = /\(\d{4}\s*[-\u2013\u2014]+\s*\d{4}\)/.test(description);
  const hasBornOnly = /\([^)]*born\s+\w+\s+\d+,\s+\d{4}\)/.test(firstSentence);
  if (hasBornOnly && !hasDeathInBrackets && !hasYearsInDescription) return false;
  const isPastTense = /^[^.]*\bwas (an?|the)\b[^.]*\./.test(extract) && !/\([^)]*born/.test(firstSentence) && !/born\s+\d{4}/.test(description);
  const diedInExtract = /\b(died|death|passed away|deceased|d\.)\b/i.test(extract);
  const diedInDescription = /\b(died|death|deceased)\b/i.test(description);
  // Also check description for year range like "American attorney (1944-2026)"
  const yearRangeInDesc = /\(\d{4}[-\u2013\u2014]+\d{4}\)/.test(description);
  return hasDeathInBrackets || hasYearsInDescription || yearRangeInDesc || isPastTense || diedInExtract || diedInDescription;
}

function App() {
  const [page, setPage] = useState('landing');
  const [auth, setAuth] = useState(false);
  const [user, setUser] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [wikiProfile, setWikiProfile] = useState(null);
  const [watchlistCheck, setWatchlistCheck] = useState(null);
  const [watchlistChecking, setWatchlistChecking] = useState(false);
  const [watchlistChecked, setWatchlistChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [backendWaking, setBackendWaking] = useState(false);
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [sName, setSName] = useState('');
  const [sLoc, setSLoc] = useState('');
  const [sBirthYear, setSBirthYear] = useState('');
  const [nw, setNw] = useState({ name: '', location: '', birthYear: '' });
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [showDangerZone, setShowDangerZone] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  // NEW: drawer now holds live refresh data, not just a wiki fetch
  const [drawerData, setDrawerData] = useState(null);
  const [drawerRefreshing, setDrawerRefreshing] = useState(false);
  const [selectedDisambig, setSelectedDisambig] = useState(null);
  const [dismissedAlerts, setDismissedAlerts] = useState([]);
  const [apiVersion, setApiVersion] = useState('...'); // chosen match from disambiguation list

  useEffect(() => {
    fetch(API_BASE + '/health').then(r => r.json()).then(d => setApiVersion(d.version || '?')).catch(() => setApiVersion('?'));
    const t = localStorage.getItem('doa_token');
    const u = localStorage.getItem('doa_user');
    if (t && u) { setUser(JSON.parse(u)); setAuth(true); setPage('watchlist'); loadWatchlist(); loadNotifications(); }
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        setTimeout(() => { document.querySelectorAll('input').forEach(i => i.blur()); }, 100);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const loadWatchlist = async () => {
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/watchlist', { headers: { 'Authorization': 'Bearer ' + token } });
      if (!r.ok) throw new Error('Failed');
      setWatchlist(await r.json());
    } catch (e) { console.error(e); }
  };

  const loadNotifications = async () => {
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/notifications', { headers: { 'Authorization': 'Bearer ' + token } });
      if (!r.ok) throw new Error('Failed');
      setNotifications(await r.json());
    } catch (e) { console.error(e); }
  };

  const dismissAlert = async (notifId) => {
    try {
      const token = localStorage.getItem('doa_token');
      await fetch(API_BASE + '/notifications/' + notifId, {
        method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token }
      });
      setDismissedAlerts(prev => [...prev, notifId]);
      await loadNotifications();
    } catch (e) {
      // If delete not supported, just hide locally
      setDismissedAlerts(prev => [...prev, notifId]);
      setNotifications(prev => prev.filter(n => n.id !== notifId));
    }
  };

  const doAuth = async () => {
    if (!email || !password) return;
    setLoading(true); setBackendWaking(false);
    const wakeTimer = setTimeout(() => setBackendWaking(true), 3000);
    try {
      const endpoint = mode === 'login' ? 'login' : 'register';
      const r = await fetch(API_BASE + '/auth/' + endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      clearTimeout(wakeTimer); setBackendWaking(false);
      if (!r.ok) { const err = await r.json(); throw new Error(err.detail || 'Auth failed'); }
      const data = await r.json();
      localStorage.setItem('doa_token', data.access_token);
      const u = { email, id: '123', name: email.split('@')[0] };
      localStorage.setItem('doa_user', JSON.stringify(u));
      setUser(u); setAuth(true); setPage('watchlist');
      loadWatchlist(); loadNotifications();
    } catch (error) { clearTimeout(wakeTimer); setBackendWaking(false); alert('Error: ' + error.message); }
    finally { setLoading(false); }
  };

  const doLogout = () => {
    localStorage.removeItem('doa_token'); localStorage.removeItem('doa_user');
    setAuth(false); setUser(null); setWatchlist([]); setNotifications([]);
    setResults([]); setWikiProfile(null); setWatchlistCheck(null);
    setWatchlistChecked(false); setSearched(false); setPage('landing');
  };

  const doDeleteAccount = async () => {
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/account', { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
      if (!r.ok) throw new Error('Failed');
      doLogout(); alert('Your account has been permanently deleted.');
    } catch (error) { alert('Error deleting account: ' + error.message); }
  };

  const clearSearch = () => { setSName(''); setSLoc(''); setSBirthYear(''); setWikiProfile(null); setResults([]); setSearched(false); setSelectedDisambig(null); };
  const clearWatchlistCheck = () => { setWatchlistCheck(null); setWatchlistChecked(false); setNw({ name: '', location: '', birthYear: '' }); setSelectedDisambig(null); };

  const fetchWikiSingle = async (title) => {
    try {
      const w = await (await fetch('https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(title))).json();
      if (!w.extract) return null;
      const extract = w.extract || '', description = w.description || '', type = w.type || '';
      if (type === 'disambiguation') return null;
      const deceased = isDeceasedCheck(extract, description, w.death_date, type);
      return { title: w.title, extract, thumbnail: w.thumbnail ? w.thumbnail.source : null, birthDate: w.birth_date || null, deathDate: deceased ? (w.death_date || 'deceased') : null, description, isDisambiguation: false };
    } catch (e) { return null; }
  };

  const fetchDisambigMatches = async (title) => {
    // Fetch the disambiguation page HTML, extract linked article titles
    try {
      const url = 'https://en.wikipedia.org/w/api.php?action=parse&page=' + encodeURIComponent(title) + '&prop=links&format=json&origin=*';
      const data = await (await fetch(url)).json();
      const links = (data.parse && data.parse.links) ? data.parse.links : [];
      // Filter to likely person links (no File:, Category:, etc.)
      const personLinks = links
        .filter(l => l.ns === 0 && l['*'] && l['*'].length > 2)
        .map(l => l['*'])
        .slice(0, 8);
      // Fetch summary for each candidate
      const results = [];
      for (const link of personLinks) {
        const profile = await fetchWikiSingle(link);
        if (profile) results.push(profile);
        if (results.length >= 5) break;
      }
      return results;
    } catch (e) { return []; }
  };

  const fetchWikiProfile = async (name) => {
    const tryWiki = async (n) => {
      const w = await (await fetch('https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(n))).json();
      return w;
    };
    try {
      // Step 1: try name with periods added to bare initials
      // "Robert S Mueller" -> "Robert S. Mueller" -> finds correct article
      const nameWithPeriods = addInitialPeriods(toTitleCase(name));
      let w = await tryWiki(nameWithPeriods);
      // Step 1b: if that didn't work, try exact name as entered
      if (!w.extract && nameWithPeriods !== toTitleCase(name)) {
        w = await tryWiki(toTitleCase(name));
      }
      // Step 2: if not found, try first+last only
      if (!w.extract) {
        const simplified = normalizeForWiki(name);
        if (simplified !== toTitleCase(name)) {
          w = await tryWiki(simplified);
        }
      }
      if (!w.extract) return { isDisambiguation: false, notFound: true };
      const extract = w.extract || '', description = w.description || '', type = w.type || '';
      if (type === 'disambiguation') {
        // Return disambiguation with matches to show list
        const matches = await fetchDisambigMatches(w.title);
        return { isDisambiguation: true, title: w.title.replace(' (disambiguation)', ''), matches };
      }
      const deceased = isDeceasedCheck(extract, description, w.death_date, type);
      return { title: w.title, extract, thumbnail: w.thumbnail ? w.thumbnail.source : null, birthDate: w.birth_date || null, deathDate: deceased ? (w.death_date || 'deceased') : null, description, isDisambiguation: false };
    } catch (e) { return null; }
  };

  // CHANGED: tap on watchlist name now calls the backend /refresh endpoint
  // which checks Wikipedia, updates DB, and returns fresh bio + status
  const openWatchlistDrawer = async (watchItem) => {
    setDrawerData({ name: watchItem.name, watchlistId: watchItem.id, profile: null, loading: true, newlyDeceased: false });
    setDrawerRefreshing(true);
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/watchlist/' + watchItem.id + '/refresh', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!r.ok) throw new Error('Refresh failed');
      const data = await r.json();
      // Build a profile object from the refresh response
      const profile = {
        title: data.name,
        extract: data.wikipedia_description || '',
        thumbnail: data.thumbnail || null,
        birthDate: data.birth_date || null,
        deathDate: data.is_deceased ? (data.death_date || data.death_year || 'deceased') : null,
        description: data.description || '',
        isDisambiguation: false
      };
      setDrawerData({ name: data.name, watchlistId: watchItem.id, profile, loading: false, newlyDeceased: data.newly_deceased });
      // Always reload watchlist so status badge updates on screen
      await loadWatchlist();
      if (data.newly_deceased) {
        await loadNotifications();
      }
    } catch (e) {
      // Fallback to direct Wikipedia fetch if backend refresh fails
      const profile = await fetchWikiProfile(watchItem.name);
      setDrawerData({ name: watchItem.name, watchlistId: watchItem.id, profile, loading: false, newlyDeceased: false });
    }
    setDrawerRefreshing(false);
  };

  const isOnWatchlist = (name) => {
    const normalized = normalizeForWiki(name).toLowerCase();
    return watchlist.some(w => {
      const stored = normalizeForWiki(w.name).toLowerCase();
      return stored === normalized || w.name.toLowerCase() === name.toLowerCase();
    });
  };

  const checkWatch = async () => {
    const name = toTitleCase(nw.name);
    if (!name.trim() || name.trim().length < 2) { alert('Please enter a name to search.'); return; }
    // No early return for already-on-watchlist -- let Wikipedia run so user sees current status
    setWatchlistChecking(true); setWatchlistCheck(null); setWatchlistChecked(false);
    try { const profile = await fetchWikiProfile(name); setWatchlistCheck({ profile, name }); setWatchlistChecked(true); }
    catch (error) { setWatchlistCheck({ profile: null, name }); setWatchlistChecked(true); }
    finally { setWatchlistChecking(false); }
  };

  const confirmAddWatch = async () => {
    if (!watchlistCheck) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/watchlist', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ name: watchlistCheck.name, location: nw.location, dob: nw.birthYear })
      });
      if (!r.ok) throw new Error('Failed');
      await loadWatchlist();
      clearWatchlistCheck();
      setPage('notifications'); // CHANGED: go to alerts page after adding
    } catch (error) { alert('Error: ' + error.message); }
    finally { setLoading(false); }
  };

  const addWatchFromSearch = async (profileTitle) => {
    if (isOnWatchlist(profileTitle)) { alert(profileTitle + ' is already on your watchlist!'); return; }
    setLoading(true);
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/watchlist', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ name: profileTitle, location: '', dob: '' })
      });
      if (!r.ok) throw new Error('Failed');
      await loadWatchlist();
      clearSearch();
      setPage('notifications'); // CHANGED: go to alerts page after adding
    } catch (error) { alert('Error: ' + error.message); }
    finally { setLoading(false); }
  };

  const delWatch = async (id) => {
    try {
      const token = localStorage.getItem('doa_token');
      const r = await fetch(API_BASE + '/watchlist/' + id, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
      if (!r.ok) throw new Error('Failed');
      await loadWatchlist();
    } catch (error) { alert('Error: ' + error.message); }
  };

  const doSearch = async () => {
    if (!sName.trim() || sName.trim().length < 2) { alert('Please enter a name to search.'); return; }
    setLoading(true); setWikiProfile(null); setResults([]); setSearched(false);
    try {
      const token = localStorage.getItem('doa_token');
      // Legacy DB search - never crash on failure
      try {
        const r = await fetch(API_BASE + '/search', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ name: toTitleCase(sName), location: sLoc || undefined, birth_year: sBirthYear || undefined })
        });
        if (r.ok) {
          const data = await r.json();
          if (Array.isArray(data)) setResults(data);
        }
      } catch (legacyErr) { console.log('Legacy search error:', legacyErr); }
      // Wikipedia search - never crash on failure
      try {
        const profile = await fetchWikiProfile(sName);
        if (profile) setWikiProfile(profile);
      } catch (wikiErr) { console.log('Wiki search error:', wikiErr); }
      setSearched(true);
    } catch (error) { console.log('Search error:', error); setSearched(true); }
    finally { setLoading(false); }
  };

  const unreadCount = notifications.length;
  const iClass = "w-full px-4 py-2.5 border border-red-900/50 rounded-lg focus:ring-2 focus:ring-red-500 text-base bg-gray-900/60 text-white placeholder-gray-400";
  const cardClass = "bg-black/35 rounded-2xl p-3 shadow-lg border border-red-900/30 backdrop-blur-sm";
  const isWide = page === 'about' || page === 'privacy';
  const containerClass = isWide ? 'w-full max-w-3xl mx-auto px-4' : 'w-full max-w-sm mx-auto px-3';

  // SingleProfileCard -- shows one person's full bio
  const SingleProfileCard = ({ profile, showAddButton, onBack }) => {
    const alreadyWatching = isOnWatchlist(profile.title);
    const isDisambig = profile.isDisambiguation;
    return (
      <div className="rounded-2xl overflow-hidden border border-red-800 shadow-lg">
        <div className={'px-5 py-2 flex items-center gap-3 ' + (profile.deathDate ? 'bg-gray-800' : isDisambig ? 'bg-yellow-600' : 'bg-green-700')}>
          <span className="text-white font-black tracking-widest text-sm">{profile.deathDate ? 'DEAD' : isDisambig ? 'UNSURE' : 'ALIVE'}</span>
          {profile.deathDate && profile.deathDate !== 'deceased' && <span className="text-white/80 text-xs ml-auto">Died: {profile.deathDate}</span>}
          {onBack && <button onClick={onBack} className="ml-auto text-white/60 text-xs underline">Back to list</button>}
        </div>
        <div className="bg-gray-900/70 p-4">
          <div className="flex gap-3 items-start mb-3">
            {profile.thumbnail ? <img src={profile.thumbnail} alt={profile.title} className="w-16 h-16 rounded-full object-cover border-2 border-red-600/50 shrink-0" /> : <div className="w-16 h-16 rounded-full bg-red-900/40 flex items-center justify-center shrink-0 text-2xl">?</div>}
            <div className="flex-1">
              <h2 className="text-white text-lg font-bold mb-1">{profile.title}</h2>
              {profile.birthDate && <p className="text-red-300 text-sm font-bold">Born: {profile.birthDate}</p>}
              {!isDisambig && <p className="text-red-400 text-xs italic mt-1">{profile.description}</p>}
            </div>
          </div>
          {!isDisambig && profile.extract && <p className="text-gray-100 text-sm leading-relaxed mb-3">{profile.extract}</p>}
          {profile.deathDate && <div className="p-2 bg-gray-700/50 border border-gray-600/30 rounded-xl mb-3"><p className="text-gray-200 text-sm text-center">This person has passed away</p></div>}
          {showAddButton && (
            <div className="space-y-2 mb-2">
              {!profile.deathDate && (alreadyWatching
                ? <button onClick={() => setPage('notifications')} className="w-full py-2 bg-green-700/30 border border-green-500/40 text-green-200 rounded-xl text-sm text-center">Already on your watchlist</button>
                : <button onClick={() => addWatchFromSearch(profile.title)} disabled={loading} className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"><PlusIcon /> Add to Watchlist</button>
              )}
              <button onClick={clearSearch} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center">Clear Search</button>
            </div>
          )}
          <div className="p-2 bg-red-900/20 border border-red-800/20 rounded-xl">
            <p className="text-red-200 text-xs">Data provided by Wikipedia. DORA donates a portion of revenues to the Wikimedia Foundation.</p>
          </div>
        </div>
      </div>
    );
  };

  // WikiCard -- handles single result OR disambiguation list
  const WikiCard = ({ profile, showAddButton }) => {
    // If we selected a specific person from disambiguation list
    if (selectedDisambig) {
      return <SingleProfileCard profile={selectedDisambig} showAddButton={showAddButton} onBack={() => setSelectedDisambig(null)} />;
    }
    // Disambiguation list
    if (profile.isDisambiguation) {
      return (
        <div className="rounded-2xl overflow-hidden border border-red-800 shadow-lg">
          <div className="px-5 py-2 bg-yellow-600">
            <span className="text-white font-black tracking-widest text-sm">MULTIPLE MATCHES</span>
          </div>
          <div className="bg-gray-900/70 p-4">
            <p className="text-gray-300 text-sm mb-1">Several people share this name.</p>
            <p className="text-yellow-300 text-xs mb-3">Tip: Add a middle name or initial (e.g. "Robert S. Mueller") to find the right person directly.</p>
            <div className="space-y-2">
              {profile.matches && profile.matches.filter(m => {
                // Only show matches where last name appears in the Wikipedia title
                const searchLastName = (result && result.name ? result.name : (watchlistCheck && watchlistCheck.name ? watchlistCheck.name : '')).trim().split(/\s+/).pop().toLowerCase();
                return searchLastName && m.title.toLowerCase().indexOf(searchLastName) !== -1;
              }).map((m, i) => (
                <button key={i} onClick={() => setSelectedDisambig(m)} className="w-full p-3 bg-gray-800/60 border border-red-900/30 rounded-xl text-left hover:bg-gray-700/60 transition-colors">
                  <div className="flex items-center gap-3">
                    {m.thumbnail ? <img src={m.thumbnail} alt={m.title} className="w-10 h-10 rounded-full object-cover border border-red-600/40 shrink-0" /> : <div className="w-10 h-10 rounded-full bg-red-900/40 flex items-center justify-center shrink-0 text-lg">?</div>}
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-bold truncate">{m.title}</p>
                      <p className="text-red-400 text-xs italic truncate">{m.description}</p>
                    </div>
                    <span className={'px-2 py-0.5 rounded-full text-xs font-bold ' + (m.deathDate ? 'bg-gray-700 text-gray-300' : 'bg-green-800 text-green-300')}>{m.deathDate ? 'DEAD' : 'ALIVE'}</span>
                  </div>
                </button>
              ))}
              {(!profile.matches || profile.matches.length === 0) && (
                <p className="text-gray-400 text-sm text-center py-3">Could not load matches. Try entering the full name including middle name.</p>
              )}
            </div>
            <button onClick={clearSearch} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center mt-3">Clear Search</button>
          </div>
        </div>
      );
    }
    // Not found
    if (profile.notFound) return null;
    // Single unambiguous result
    return <SingleProfileCard profile={profile} showAddButton={showAddButton} />;
  };

    const WatchlistCheckCard = () => {
    if (!watchlistCheck) return null;
    const { profile, name } = watchlistCheck;

    // Disambiguation list for watchlist check
    if (profile && profile.isDisambiguation) {
      if (selectedDisambig) {
        // User picked one -- show full card with add option
        const isDeceased = selectedDisambig.deathDate;
        return (
          <div className="rounded-2xl overflow-hidden border border-red-800 shadow-lg">
            <div className={'px-5 py-2 flex items-center gap-3 ' + (isDeceased ? 'bg-gray-800' : 'bg-green-700')}>
              <span className="text-white font-black tracking-widest text-sm">{isDeceased ? 'DEAD' : 'ALIVE'}</span>
              {isDeceased && selectedDisambig.deathDate !== 'deceased' && <span className="text-white/80 text-xs ml-auto">Died: {selectedDisambig.deathDate}</span>}
              <button onClick={() => setSelectedDisambig(null)} className="ml-auto text-white/60 text-xs underline">Back</button>
            </div>
            <div className="bg-gray-900/70 p-4">
              <div className="flex gap-3 items-start mb-3">
                {selectedDisambig.thumbnail ? <img src={selectedDisambig.thumbnail} alt={selectedDisambig.title} className="w-16 h-16 rounded-full object-cover border-2 border-red-600/50 shrink-0" /> : <div className="w-16 h-16 rounded-full bg-red-900/40 flex items-center justify-center shrink-0 text-2xl">?</div>}
                <div className="flex-1">
                  <h2 className="text-white text-lg font-bold mb-1">{selectedDisambig.title}</h2>
                  {selectedDisambig.birthDate && <p className="text-red-300 text-sm font-bold">Born: {selectedDisambig.birthDate}</p>}
                  <p className="text-red-400 text-xs italic mt-1">{selectedDisambig.description}</p>
                </div>
              </div>
              {selectedDisambig.extract && <p className="text-gray-100 text-sm leading-relaxed mb-3">{selectedDisambig.extract}</p>}
              {isDeceased && <div className="p-2 bg-gray-700/50 border border-gray-600/30 rounded-xl mb-3"><p className="text-gray-200 text-sm text-center">This person has passed away.{selectedDisambig.deathDate !== 'deceased' ? ' Died: ' + selectedDisambig.deathDate : ''}</p></div>}
              {!isDeceased && (
                <div className="space-y-2 mt-2">
                  <p className="text-white/80 text-sm text-center font-medium border-t border-white/10 pt-2">Add {selectedDisambig.title} to watchlist?</p>
                  <button onClick={() => { setWatchlistCheck({ ...watchlistCheck, name: selectedDisambig.title }); confirmAddWatch(); }} disabled={loading} className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                    <PlusIcon /> {loading ? 'Adding...' : 'Yes, Add to Watchlist'}
                  </button>
                  <button onClick={() => setSelectedDisambig(null)} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center">Back to list</button>
                </div>
              )}
              {isDeceased && <button onClick={clearWatchlistCheck} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center mt-2">Try Another Name</button>}
            </div>
          </div>
        );
      }
      // Show disambiguation list
      return (
        <div className="rounded-2xl overflow-hidden border border-red-800 shadow-lg">
          <div className="px-5 py-2 bg-yellow-600">
            <span className="text-white font-black tracking-widest text-sm">MULTIPLE MATCHES</span>
          </div>
          <div className="bg-gray-900/70 p-4">
            <p className="text-gray-300 text-sm mb-1">Several people share this name.</p>
            <p className="text-yellow-300 text-xs mb-3">Tip: Add a middle name or initial (e.g. "Robert S. Mueller") to find the right person directly.</p>
            <div className="space-y-2">
              {profile.matches && profile.matches.filter(m => {
                // Only show matches where last name appears in the Wikipedia title
                const searchLastName = (result && result.name ? result.name : (watchlistCheck && watchlistCheck.name ? watchlistCheck.name : '')).trim().split(/\s+/).pop().toLowerCase();
                return searchLastName && m.title.toLowerCase().indexOf(searchLastName) !== -1;
              }).map((m, i) => (
                <button key={i} onClick={() => setSelectedDisambig(m)} className="w-full p-3 bg-gray-800/60 border border-red-900/30 rounded-xl text-left hover:bg-gray-700/60 transition-colors">
                  <div className="flex items-center gap-3">
                    {m.thumbnail ? <img src={m.thumbnail} alt={m.title} className="w-10 h-10 rounded-full object-cover border border-red-600/40 shrink-0" /> : <div className="w-10 h-10 rounded-full bg-red-900/40 flex items-center justify-center shrink-0 text-lg">?</div>}
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-bold truncate">{m.title}</p>
                      <p className="text-red-400 text-xs italic truncate">{m.description}</p>
                    </div>
                    <span className={'px-2 py-0.5 rounded-full text-xs font-bold ' + (m.deathDate ? 'bg-gray-700 text-gray-300' : 'bg-green-800 text-green-300')}>{m.deathDate ? 'DEAD' : 'ALIVE'}</span>
                  </div>
                </button>
              ))}
              {(!profile.matches || profile.matches.length === 0) && (
                <p className="text-gray-400 text-sm text-center py-3">Could not load matches. Try entering the full name including middle name.</p>
              )}
            </div>
            <button onClick={() => { setWatchlistChecked(false); setWatchlistCheck(null); setSelectedDisambig(null); }} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center mt-3 flex items-center justify-center gap-2">
              <EditIcon /> Try a different name
            </button>
          </div>
        </div>
      );
    }

    const isDeceased = profile && profile.deathDate;
    const isDisambig = false;
    const notFound = !profile || profile.notFound;
    return (
      <div className="rounded-2xl overflow-hidden border border-red-800 shadow-lg">
        <div className={'px-5 py-2 ' + (isDeceased ? 'bg-gray-800' : notFound ? 'bg-blue-700' : 'bg-green-700')}>
          <span className="text-white font-black tracking-widest text-sm">{isDeceased ? 'DEAD' : notFound ? 'NOT IN WIKIPEDIA' : 'ALIVE'}</span>
        </div>
        <div className="bg-gray-900/70 p-4">
          {profile && !notFound && (
            <>
              <div className="flex gap-3 items-start mb-3">
                {profile.thumbnail ? <img src={profile.thumbnail} alt={profile.title} className="w-16 h-16 rounded-full object-cover border-2 border-red-600/50 shrink-0" /> : <div className="w-16 h-16 rounded-full bg-red-900/40 flex items-center justify-center shrink-0 text-2xl">?</div>}
                <div className="flex-1">
                  <h2 className="text-white text-lg font-bold mb-1">{profile.title}</h2>
                  {profile.birthDate && <p className="text-red-300 text-sm font-bold">Born: {profile.birthDate}</p>}
                  <p className="text-red-400 text-xs italic mt-1">{profile.description}</p>
                </div>
              </div>
              {profile.extract && <p className="text-gray-100 text-sm leading-relaxed mb-3">{profile.extract}</p>}
            </>
          )}
          {notFound && <div className="mb-3"><p className="text-white text-base font-bold mb-1">"{name}"</p><p className="text-gray-300 text-sm">No Wikipedia result found.</p></div>}
          {isDeceased && <div className="p-2 bg-gray-700/50 border border-gray-600/30 rounded-xl mb-3"><p className="text-gray-200 text-sm text-center">This person has passed away.{profile.deathDate && profile.deathDate !== 'deceased' ? ' Died: ' + profile.deathDate : ''}</p></div>}
          {!isDeceased && (
            <div className="space-y-2 mt-2">
              <p className="text-white/80 text-sm text-center font-medium border-t border-white/10 pt-2">
                {notFound ? 'Add "' + name + '" to watchlist?' : 'Add ' + (profile ? profile.title : name) + ' to watchlist?'}
              </p>
              {isOnWatchlist(profile ? profile.title : name)
                ? <p className="w-full py-2.5 text-center text-green-400 text-sm font-bold">Already on your watchlist</p>
                : <button onClick={confirmAddWatch} disabled={loading} className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                    <PlusIcon /> {loading ? 'Adding...' : 'Yes, Add to Watchlist'}
                  </button>
              }
              <button onClick={() => { setWatchlistChecked(false); setWatchlistCheck(null); setSelectedDisambig(null); }} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center flex items-center justify-center gap-2">
                <EditIcon /> Edit Name
              </button>
              <button onClick={clearWatchlistCheck} className="w-full py-1.5 text-white/40 text-xs text-center">Cancel</button>
            </div>
          )}
          {isDeceased && <button onClick={clearWatchlistCheck} className="w-full py-2 bg-white/10 border border-white/20 text-white/80 rounded-xl text-sm text-center mt-2">Try Another Name</button>}
        </div>
      </div>
    );
  };

    const WikiDrawer = () => {
    if (!drawerData) return null;
    const { name, profile, loading: drawerLoading, newlyDeceased } = drawerData;
    return (
      <>
        <div className="modal-overlay" onClick={() => setDrawerData(null)} />
        <div className="modal-drawer">
          <div className="flex justify-between items-center px-4 pt-4 pb-2 border-b border-red-900/30">
            <h3 className="text-white font-bold text-lg">{name}</h3>
            <button onClick={() => setDrawerData(null)} className="text-gray-400 hover:text-white text-2xl font-bold">X</button>
          </div>
          <div className="p-4">
            {drawerLoading && (
              <div className="text-center py-8">
                <p className="text-white animate-pulse">Checking Wikipedia...</p>
              </div>
            )}
            {!drawerLoading && !profile && (
              <div className="text-center py-8">
                <p className="text-4xl mb-3">?</p>
                <p className="text-white font-bold text-lg">Bio not available</p>
                <p className="text-gray-300 text-sm mt-2">No Wikipedia entry found for "{name}"</p>
                <p className="text-gray-400 text-xs mt-2">Try searching with full name including middle name</p>
              </div>
            )}
            {!drawerLoading && profile && (
              <>
                <div className={'px-4 py-2 rounded-xl mb-4 flex items-center gap-3 ' + (profile.deathDate ? 'bg-gray-700' : profile.isDisambiguation ? 'bg-yellow-600' : 'bg-green-700')}>
                  <span className="text-white font-black">{profile.deathDate ? 'DECEASED' : profile.isDisambiguation ? 'UNSURE' : 'ALIVE'}</span>
                  {profile.deathDate && <span className="text-white/80 text-sm ml-auto">{profile.deathDate !== 'deceased' ? 'Died: ' + profile.deathDate : 'Deceased'}</span>}
                </div>
                {newlyDeceased && (
                  <div className="p-3 bg-red-900/60 border border-red-600 rounded-xl mb-4">
                    <p className="text-red-200 text-sm text-center font-bold">Status just updated -- this person has passed away. Notification sent.</p>
                  </div>
                )}
                <div className="flex gap-3 items-start mb-4">
                  {profile.thumbnail ? <img src={profile.thumbnail} alt={profile.title} className="w-20 h-20 rounded-full object-cover border-2 border-red-600/50 shrink-0" /> : <div className="w-20 h-20 rounded-full bg-red-900/40 flex items-center justify-center shrink-0 text-3xl">?</div>}
                  <div className="flex-1">
                    <h2 className="text-white text-xl font-bold mb-1">{profile.title}</h2>
                    {profile.birthDate && <p className="text-red-300 text-sm font-bold">Born: {profile.birthDate}</p>}
                    {!profile.isDisambiguation && <p className="text-red-400 text-xs italic mt-1">{profile.description}</p>}
                  </div>
                </div>
                {!profile.isDisambiguation && profile.extract && <p className="text-gray-100 text-sm leading-relaxed mb-4">{profile.extract}</p>}
                {profile.isDisambiguation && <div className="p-3 bg-yellow-500/20 border border-yellow-400/30 rounded-xl mb-4"><p className="text-yellow-200 text-sm text-center">Multiple people share this name</p></div>}
              </>
            )}
            <button onClick={() => setDrawerData(null)} className="w-full py-3 bg-red-900/40 border border-red-800/50 text-white rounded-xl text-sm mt-2">Close</button>
          </div>
        </div>
      </>
    );
  };

  if (page === 'landing') {
    return (
      <div onClick={() => setPage('login')} style={{ minHeight: '100dvh', width: '100%', cursor: 'pointer', position: 'relative', ...POSTER_STYLE }}>
        <div style={{ position: 'absolute', top: TAP_TOP, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
          <div className="tap-pulse" style={{ color: 'white', fontSize: isPhone ? '1.2rem' : '1.1rem', fontWeight: '900', letterSpacing: '0.12em', textShadow: '0 2px 8px rgba(0,0,0,0.9)', textAlign: 'center' }}>TAP TO ENTER</div>
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>Free during beta</div>
        </div>
      </div>
    );
  }

  if (page === 'login') {
    return (
      <div style={{ minHeight: '100dvh', width: '100%', ...POSTER_STYLE, display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: PT, paddingLeft: '1.5rem', paddingRight: '1.5rem', paddingBottom: '2rem' }}>
        <div style={{ width: '100%', maxWidth: '22rem' }}>
          <div className="bg-black/50 backdrop-blur-sm rounded-2xl p-4 shadow-2xl border border-red-900/40 space-y-3">
            <div className="text-center">
              <h1 className="text-white text-lg font-black tracking-widest">DEAD OR ALIVE</h1>
              <p className="text-red-300 text-base mt-1 font-bold">Find out if the people you remember are dead or alive</p>
              <p className="text-white/50 text-xs mt-1">Free during beta</p>
            </div>
            <input type="email" placeholder="Email address" value={email} onChange={(e) => setEmail(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && doAuth()} className="w-full px-4 py-2 rounded-xl bg-white/15 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-red-500 text-base" />
            <div className="relative">
              <input type={showPassword ? 'text' : 'password'} placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && doAuth()} className="w-full px-4 py-2 rounded-xl bg-white/15 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-red-500 text-base" />
              <button onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60">{showPassword ? <EyeOffIcon /> : <EyeIcon />}</button>
            </div>
            {backendWaking && <p className="text-white/60 text-xs text-center animate-pulse">Waking up the server...</p>}
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => { setMode('login'); doAuth(); }} disabled={loading} className="py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl disabled:opacity-50 text-base">{loading && mode === 'login' ? '...' : 'Sign In'}</button>
              <button onClick={() => { setMode('register'); doAuth(); }} disabled={loading} className="py-2 bg-white/20 hover:bg-white/30 text-white font-bold rounded-xl disabled:opacity-50 text-base border border-white/30">{loading && mode === 'register' ? '...' : 'Register'}</button>
            </div>
            <p className="text-white/40 text-xs text-center">You'll stay signed in automatically</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <PageWrapper>
      <WikiDrawer />
      <div className={containerClass}>

        {page === 'watchlist' && (
          <div className="space-y-3" style={{ paddingTop: PT }}>
            <div className={cardClass}>
              <CardPageHeader title="Watchlist" subtitle="Add a person to monitor -- we'll alert you when their status changes" onHome={() => setPage('watchlist')} />
              {!watchlistChecked ? (
                <div className="space-y-3">
                  <ClearableInput value={nw.name} onChange={(e) => setNw({...nw, name: e.target.value})} onBlur={(e) => setNw({...nw, name: toTitleCase(e.target.value)})} onKeyPress={(e) => e.key === 'Enter' && checkWatch()} placeholder="Full Name" inputClass={iClass} />
                  <ClearableInput value={nw.location} onChange={(e) => setNw({...nw, location: e.target.value})} onKeyPress={(e) => e.key === 'Enter' && checkWatch()} placeholder="City and/or State (optional)" inputClass={iClass} />
                  <ClearableInput value={nw.birthYear} onChange={(e) => setNw({...nw, birthYear: e.target.value.replace(/\D/g, '').slice(0, 4)})} onKeyPress={(e) => e.key === 'Enter' && checkWatch()} placeholder="Birth Year (optional)" maxLength={4} inputClass={iClass} />
                  <button onClick={checkWatch} disabled={watchlistChecking} className="w-full py-3 bg-red-600 text-white rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 text-base font-bold">
                    <SearchIcon /> {watchlistChecking ? 'Checking...' : 'Check Name'}
                  </button>
                </div>
              ) : <WatchlistCheckCard />}
            </div>
          </div>
        )}

        {page === 'search' && (
          <div className="space-y-3" style={{ paddingTop: PT }}>
            <div className={cardClass}>
              <CardPageHeader title="Search" subtitle="Look up anyone by name -- dead or alive" onHome={() => setPage('watchlist')} />
              <div className="space-y-3">
                <ClearableInput value={sName} onChange={(e) => { setSName(e.target.value); setWikiProfile(null); setResults([]); setSearched(false); }} onKeyPress={(e) => e.key === 'Enter' && doSearch()} placeholder="Name (first, last, or full)" inputClass={iClass} />
                <ClearableInput value={sLoc} onChange={(e) => setSLoc(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && doSearch()} placeholder="City and/or State (optional)" inputClass={iClass} />
                <ClearableInput value={sBirthYear} onChange={(e) => setSBirthYear(e.target.value.replace(/\D/g, '').slice(0, 4))} onKeyPress={(e) => e.key === 'Enter' && doSearch()} placeholder="Birth Year (optional)" maxLength={4} inputClass={iClass} />
                <button onClick={doSearch} disabled={loading} className="w-full py-2.5 bg-red-600 text-white rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 text-base font-bold">
                  <SearchIcon /> {loading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>
            {wikiProfile && !loading && <WikiCard profile={wikiProfile} showAddButton={true} />}
            {!loading && searched && !wikiProfile && results.length === 0 && (
              <div className={cardClass + " text-center"}>
                <p className="text-3xl mb-2">?</p>
                <h3 className="font-bold text-white text-xl mb-1">No results for "{sName}"</h3>
                <p className="text-gray-300 text-base">Try checking spelling or a middle name.</p>
              </div>
            )}
            {results.length > 0 && (
              <div className={cardClass}>
                <h2 className="text-xl font-bold mb-1 text-white text-center">Obituary Records ({results.length})</h2>
                <p className="text-sm text-gray-200 mb-3 text-center">Records found in our Legacy database</p>
                <div className="space-y-3">
                  {results.map(r => (
                    <div key={r.id} className="p-3 border border-red-900/30 rounded-lg bg-gray-800/50">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-base text-white">{r.name}</h3>
                        <span className={'px-2 py-1 rounded-full text-xs ' + (r.confidence === 'high' ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300')}>{r.confidence}</span>
                      </div>
                      <div className="text-sm text-gray-300 space-y-1">
                        {r.age && <p>Age: {r.age}</p>}
                        <p>Location: {r.location || 'Unknown'}</p>
                        <p>Date: {r.date || 'Unknown'}</p>
                      </div>
                      {r.obit_text && <p className="text-sm text-gray-300 mt-2 leading-relaxed border-t border-red-900/30 pt-2">{r.obit_text.slice(0, 300)}{r.obit_text.length > 300 ? '...' : ''}</p>}
                      {r.link && <a href={r.link} target="_blank" rel="noopener noreferrer" className="text-red-400 text-xs mt-2 block">Read full obituary</a>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* CHANGED: notifications page now shows watchlist list below alerts */}
        {page === 'notifications' && (
          <div className="space-y-3" style={{ paddingTop: PT }}>
            <div className={cardClass}>
              <CardPageHeader title="Alerts" subtitle="Status changes for people on your watchlist" onHome={() => setPage('watchlist')} />
              {notifications.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-white font-bold text-xl">No alerts yet</p>
                  <p className="text-gray-200 text-base mt-1">We'll alert you when someone on your watchlist passes away</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {notifications.map(n => (
                    <div key={n.id} className="p-3 bg-red-950/50 border border-red-800 rounded-xl">
                      <div className="flex items-start gap-3">
                        <div className="flex-1">
                          <h3 className="font-bold text-white text-base">{n.name}</h3>
                          <p className="text-gray-300 text-sm mt-1">{n.message}</p>
                          <p className="text-gray-500 text-xs mt-1">{new Date(n.created_at).toLocaleDateString()}</p>
                        </div>
                        <button onClick={() => dismissAlert(n.id)} className="text-gray-500 hover:text-red-400 text-xs px-2 py-1 border border-gray-700 rounded-lg shrink-0">Dismiss</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {/* Watchlist list below alerts */}
            <div className={cardClass}>
              <h2 className="text-xl font-bold mb-0.5 text-white text-center">Your Watchlist ({watchlist.length})</h2>
              <p className="text-sm text-gray-200 mb-3 text-center">Tap a name to check their current status</p>
              {watchlist.length === 0 ? <p className="text-gray-400 text-center py-6">No one on your watchlist yet</p> : (
                <div className="space-y-3">
                  {watchlist.map(w => (
                    <div key={w.id} className={'p-3 rounded-lg border ' + (w.is_deceased ? 'bg-gray-900/70 border-gray-600/50' : 'bg-gray-800/50 border-red-900/20')}>
                      {editingId === w.id ? (
                        <div className="space-y-2">
                          <ClearableInput value={editingName} onChange={(e) => setEditingName(e.target.value)} placeholder="Enter name" inputClass="w-full px-3 py-2 border border-red-700 rounded-lg focus:ring-2 focus:ring-red-500 text-base bg-gray-700 text-white placeholder-gray-400" />
                          <div className="flex gap-2">
                            <button onClick={async () => {
                              await delWatch(w.id);
                              const token = localStorage.getItem('doa_token');
                              await fetch(API_BASE + '/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }, body: JSON.stringify({ name: toTitleCase(editingName), location: w.location, dob: w.dob }) });
                              await loadWatchlist(); setEditingId(null); setEditingName('');
                            }} className="flex-1 py-2 bg-red-600 text-white rounded-lg text-sm font-bold">Save</button>
                            <button onClick={() => { setEditingId(null); setEditingName(''); }} className="flex-1 py-2 bg-gray-600 text-gray-200 rounded-lg text-sm">Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <button onClick={() => openWatchlistDrawer(w)} className="text-left w-full">
                              <h3 className={'font-semibold text-base underline decoration-dotted truncate ' + (w.is_deceased ? 'text-gray-400 line-through' : 'text-white hover:text-red-300')}>{w.name}</h3>
                            </button>
                            <div className="text-sm text-gray-300">{w.location && <span>{w.location}</span>}{w.dob && <span> - Born: {w.dob}</span>}</div>
                            <div className="flex items-center gap-1 mt-1">
                              {w.is_deceased
                                ? <span className="text-xs text-red-400 font-bold">DECEASED</span>
                                : <><CheckIcon /><span className="text-xs text-green-400">Active</span></>
                              }
                            </div>
                          </div>
                          <div className="flex gap-2 ml-2 shrink-0">
                            <button onClick={() => { setEditingId(w.id); setEditingName(w.name); }} className="p-2 text-red-400 hover:bg-red-900/30 rounded-lg"><EditIcon /></button>
                            <button onClick={() => delWatch(w.id)} className="p-2 text-red-500 hover:bg-red-900/30 rounded-lg"><TrashIcon /></button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {page === 'about' && (
          <div className="space-y-4 pb-8" style={{ paddingTop: '1rem' }}>
            <div className={cardClass}>
              <CardPageHeader title="About Dead or Alive" onHome={() => setPage('watchlist')} />
              <p className="text-red-300 italic text-base leading-relaxed mb-4">Find people you miss. Find out if they are dead or alive.</p>
              <div className="space-y-3 text-gray-200 text-sm leading-relaxed">
                <p>Dead or Alive was built by three brains -- mine, ChatGPT, and Claude (Anthropic). I'm a retired 74 year old former high-tech entrepreneur. As I get older, I look at the obituaries and wonder about old friends. Did they make it? Are they still out there?</p>
                <p>Traditional search engines are frustrating for this. So I built Dead or Alive -- a straight answer to a simple question, with a watchlist that alerts you the moment someone passes away.</p>
                <p>We partner with Legacy, the largest obituary platform in the US, covering more than 70% of all U.S. deaths. We also partner with Wikipedia for biographical information on notable people.</p>
                <p>If you have thoughts on how to improve Dead or Alive, please reach out!</p>
              </div>
              <div className="mt-4 pt-4 border-t border-red-900/30">
                <div className="flex items-center gap-4">
                  <img src={BILL_PHOTO} alt="Bill Spencer" className="w-14 h-14 rounded-full object-cover border-2 border-red-600 shadow-lg" />
                  <div>
                    <p className="font-bold text-white text-base">Bill Spencer</p>
                    <p className="text-red-400 italic text-sm">Idea Hamster</p>
                    <a href="mailto:bspencer413@me.com" className="text-red-400 text-xs mt-1 block">bspencer413@me.com</a>
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-red-900/30">
                <div className="p-3 bg-gray-800/50 rounded-lg mb-3"><p className="font-medium text-gray-200 text-sm text-center">{user && user.email}</p></div>
                <button onClick={doLogout} className="w-full py-3 bg-red-700 text-white rounded-lg text-base font-bold mb-3">Sign Out</button>
                <div className="pt-3 border-t border-red-900/30">
                  <button onClick={() => setShowDangerZone(!showDangerZone)} className="w-full py-2 text-gray-500 text-sm text-center">{showDangerZone ? 'Hide' : 'Account Removal'}</button>
                  {showDangerZone && (
                    <div className="mt-3 space-y-3">
                      {!showDeleteConfirm
                        ? <button onClick={() => setShowDeleteConfirm(true)} className="w-full py-3 bg-gray-900/70 border border-red-800 text-red-500 rounded-lg text-sm">Delete Account</button>
                        : <div className="bg-red-950/90 border border-red-800 rounded-2xl p-5 space-y-3">
                            <h3 className="font-bold text-red-400 text-lg">Are you sure?</h3>
                            <p className="text-red-300 text-base">This will permanently delete your account and all watchlist data.</p>
                            <button onClick={doDeleteAccount} className="w-full py-3 bg-red-700 text-white rounded-lg font-bold">Yes, Permanently Delete My Account</button>
                            <button onClick={() => { setShowDeleteConfirm(false); setShowDangerZone(false); }} className="w-full py-3 bg-gray-800 border border-gray-600 text-gray-300 rounded-lg font-medium">Cancel</button>
                          </div>
                      }
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className={cardClass}>
              <h3 className="font-bold text-white mb-1">Privacy Policy</h3>
              <p className="text-gray-400 text-xs mb-3">Last updated: March 17, 2026</p>
              <div className="space-y-3 text-gray-200 text-sm leading-relaxed">
                <p><strong className="text-white">Information We Collect:</strong> Your email address, watchlist names, search queries, and anonymous usage data.</p>
                <p><strong className="text-white">How We Use It:</strong> We do not sell your personal information. Ever.</p>
                <p><strong className="text-white">Data Sources:</strong> Search results are powered by Legacy obituary feeds and Wikipedia.</p>
                <p><strong className="text-white">Your Rights:</strong> You may delete your account and all data from this page at any time.</p>
                <a href="mailto:bspencer413@me.com" className="text-red-400">bspencer413@me.com</a>
              </div>
            </div>
            <p className="text-white/30 text-center text-xs pb-4">v{APP_VERSION}</p>
          </div>
        )}

      </div>

      {/* NAV: 3 items - Watchlist (home), About, Bell */}
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, backgroundColor: 'rgba(10,0,0,0.95)', backdropFilter: 'blur(8px)', borderTop: '1px solid #7f1d1d', padding: '0.5rem 1rem', paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))' }}>
        <div className="flex justify-around max-w-sm mx-auto">
          <button onClick={() => setPage('watchlist')} className={'flex flex-col items-center gap-0.5 px-3 py-1 ' + (page === 'watchlist' ? 'text-red-500' : 'text-gray-400')}>
            <HeartIcon /><span className="text-xs font-medium">Watchlist</span>
          </button>
          <button onClick={() => setPage('about')} className={'flex flex-col items-center gap-0.5 px-3 py-1 ' + (page === 'about' ? 'text-red-500' : 'text-gray-400')}>
            <InfoIcon /><span className="text-xs font-medium">About</span>
          </button>
          <button onClick={() => setPage('notifications')} className={'flex flex-col items-center gap-0.5 px-3 py-1 relative ' + (page === 'notifications' ? 'text-red-500' : 'text-gray-400')}>
            <BellIcon red={unreadCount > 0} />
            {unreadCount > 0 && <span className="absolute top-0 right-1 bg-red-600 text-white text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">{unreadCount > 9 ? '9+' : unreadCount}</span>}
            <span className="text-xs font-medium" style={unreadCount > 0 ? {color:'#dc2626'} : {}}>Alerts</span>
          </button>
        </div>
        <p className="text-center text-gray-600 text-xs mt-1">app v{APP_VERSION} | api v{apiVersion}</p>
      </div>
    </PageWrapper>
  );
}

ReactDOM.render(React.createElement(App), document.getElementById('root'));
</script>
</body>
</html>