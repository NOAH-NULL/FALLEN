import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, ArrowDownRight, ArrowUpRight, Bell, Bot, ChevronDown, ChevronLeft,
  ChevronRight, CircleHelp, Command, ExternalLink, Gauge, LayoutDashboard,
  LockKeyhole, Menu, MessageSquare, MoreHorizontal, Radio, Search, Settings2,
  Shield, ShieldAlert, ShieldCheck, SlidersHorizontal, Sparkles, Users, X,
  Zap, Check, Clock3, Hash, Server, Terminal, Eye, RefreshCw
} from 'lucide-react';
import './styles.css';

const initialEvents = [
  { type: 'shield', title: 'Anti-nuke protection active', detail: 'No destructive activity detected', time: '2 min ago', tone: 'green' },
  { type: 'users', title: 'Member joined', detail: 'New arrival in your community', time: '8 min ago', tone: 'blue' },
  { type: 'message', title: 'Automod rule triggered', detail: 'A message was held for review', time: '14 min ago', tone: 'red' },
  { type: 'settings', title: 'Configuration synced', detail: 'Latest settings loaded', time: '26 min ago', tone: 'purple' },
];

const nav = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Moderation', icon: Shield },
  { label: 'AutoMod', icon: ShieldAlert },
  { label: 'Welcome', icon: MessageSquare },
  { label: 'Leveling', icon: Zap },
  { label: 'Community', icon: Users },
];
const bottomNav = [{ label: 'Activity logs', icon: Activity }, { label: 'Settings', icon: Settings2 }];

function App() {
  const [active, setActive] = useState('Overview');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showConnect, setShowConnect] = useState(false);
  const [query, setQuery] = useState('');
  const [guild, setGuild] = useState('Sovereign Void');
  const [toast, setToast] = useState('');
  const [toggles, setToggles] = useState({ antiNuke: true, antiRaid: true, automod: true, joinAlerts: false });
  const [events, setEvents] = useState(initialEvents);
  const filteredEvents = events.filter(e => (e.title + ' ' + e.detail).toLowerCase().includes(query.toLowerCase()));

  function notify(message) {
    setToast(message);
    window.setTimeout(() => setToast(''), 2600);
  }
  function flip(key) {
    setToggles(prev => ({ ...prev, [key]: !prev[key] }));
    notify('Demo preview only — connect the API to save server settings.');
  }
  function choose(label) {
    setActive(label);
    setMobileOpen(false);
  }

  return <div className="app-shell">
    {mobileOpen && <button className="mobile-scrim" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
    <aside className={'sidebar ' + (mobileOpen ? 'sidebar-open' : '')}>
      <div className="brand-row">
        <div className="brand-mark"><span>F</span><i /></div>
        <div className="brand-copy"><strong>FALLEN</strong><small>CONTROL CENTER <span>V0.1</span></small></div>
        <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={17}/></button>
      </div>
      <button className="workspace-switch" onClick={() => notify('Guild picker will use Discord OAuth once the API is configured.')}>
        <div className="guild-avatar">S</div><div className="workspace-copy"><strong>{guild}</strong><small>Community server</small></div><ChevronDown size={15} />
      </button>
      <div className="side-label">WORKSPACE</div>
      <nav className="nav-list">
        {nav.map(({label, icon: Icon}) => <button key={label} className={'nav-item ' + (active === label ? 'active' : '')} onClick={() => choose(label)}><Icon size={17}/><span>{label}</span>{label === 'Moderation' && <span className="nav-count">4</span>}</button>)}
      </nav>
      <div className="side-label tools-label">MANAGE</div>
      <nav className="nav-list">
        {bottomNav.map(({label, icon: Icon}) => <button key={label} className={'nav-item ' + (active === label ? 'active' : '')} onClick={() => choose(label)}><Icon size={17}/><span>{label}</span></button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="status-mini"><span className="status-dot" /><div><strong>Dashboard preview</strong><small>API not connected</small></div><MoreHorizontal size={16}/></div>
        <button className="profile-row" onClick={() => setShowConnect(true)}><div className="profile-avatar">N</div><div className="profile-copy"><strong>Not connected</strong><small>Connect Discord account</small></div><ChevronRight size={15}/></button>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="topbar-left"><button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={19}/></button><div className="breadcrumbs"><span>Workspace</span><ChevronRight size={14}/><strong>{active}</strong></div></div>
        <div className="topbar-right"><div className="command-search"><Search size={15}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search activity..." /><kbd>⌘ K</kbd></div><button className="icon-button notification-button" onClick={() => notify('You’re all caught up.')} aria-label="Notifications"><Bell size={17}/><i /></button><button className="connect-button" onClick={() => setShowConnect(true)}><span className="discord-mark">◉</span> Connect Discord</button></div>
      </header>

      <div className="content-wrap">
        <section className="welcome-header">
          <div><div className="eyebrow"><span className="eyebrow-line"/> SYSTEM OVERVIEW</div><h1>{active === 'Overview' ? 'Your server, in control.' : active + '.'}</h1><p>{active === 'Overview' ? 'A clear view of what’s happening across your community.' : 'Manage and monitor your community from one place.'}</p></div>
          <div className="header-actions"><span className="preview-pill"><span/> PREVIEW MODE</span><button className="secondary-button" onClick={() => { setEvents(initialEvents); notify('Preview data refreshed.'); }}><RefreshCw size={14}/> Refresh</button></div>
        </section>

        <section className="notice-banner"><div className="notice-icon"><LockKeyhole size={18}/></div><div className="notice-copy"><strong>Control Center is running in preview mode</strong><span>Connect the FastAPI service and Discord OAuth to load real server data. No settings are being changed.</span></div><button onClick={() => setShowConnect(true)}>Set up connection <ChevronRight size={15}/></button><button className="notice-close" onClick={e => e.currentTarget.parentElement.remove()} aria-label="Dismiss notice"><X size={15}/></button></section>

        <section className="section-heading"><div><h2>Server snapshot</h2><p>Quick signals from your selected community</p></div><button className="subtle-button" onClick={() => choose('Activity logs')}>View activity <ArrowUpRight size={14}/></button></section>
        <section className="stats-grid">
          <StatCard icon={Users} label="Total members" value="—" note="Waiting for Discord" color="purple" />
          <StatCard icon={ShieldCheck} label="Threats blocked" value="—" note="Live security feed unavailable" color="green" />
          <StatCard icon={MessageSquare} label="Messages today" value="—" note="Waiting for bot telemetry" color="blue" />
          <StatCard icon={Activity} label="Bot uptime" value="—" note="API health not connected" color="orange" />
        </section>

        <section className="middle-grid">
          <div className="panel security-panel">
            <div className="panel-head"><div><div className="panel-icon red-icon"><ShieldCheck size={17}/></div><div><h3>Security posture</h3><p>Protection modules overview</p></div></div><button className="icon-button" onClick={() => choose('Settings')} aria-label="Security settings"><SlidersHorizontal size={16}/></button></div>
            <div className="security-score"><div className="score-ring"><ShieldCheck size={25}/></div><div><strong>Protected by design</strong><span>Connect to verify live protection status.</span></div><span className="unverified-tag">UNVERIFIED</span></div>
            <div className="toggle-list">
              <ToggleRow title="Anti-nuke" desc="Destructive action monitoring" enabled={toggles.antiNuke} onClick={() => flip('antiNuke')} />
              <ToggleRow title="Anti-raid" desc="Join-spike detection" enabled={toggles.antiRaid} onClick={() => flip('antiRaid')} />
              <ToggleRow title="AutoMod" desc="Automated message checks" enabled={toggles.automod} onClick={() => flip('automod')} />
              <ToggleRow title="Join alerts" desc="Notify staff about new members" enabled={toggles.joinAlerts} onClick={() => flip('joinAlerts')} />
            </div>
            <div className="panel-foot"><span><LockKeyhole size={13}/> Preview only · changes are not saved</span><button onClick={() => choose('Settings')}>Security settings <ChevronRight size={14}/></button></div>
          </div>

          <div className="panel activity-panel">
            <div className="panel-head"><div><div className="panel-icon blue-icon"><Radio size={17}/></div><div><h3>Recent activity</h3><p>Latest events from your server</p></div></div><button className="icon-button" onClick={() => { setEvents(initialEvents); notify('Activity list reset to sample events.'); }} aria-label="Refresh activity"><RefreshCw size={15}/></button></div>
            <div className="event-list">
              {filteredEvents.length ? filteredEvents.map((event, index) => <EventRow key={event.title} event={event} last={index === filteredEvents.length - 1}/>) : <div className="empty-state">No matching events. Try another search.</div>}
            </div>
            <button className="view-all" onClick={() => choose('Activity logs')}>View all activity <ArrowUpRight size={14}/></button>
          </div>
        </section>

        <section className="bottom-grid">
          <div className="panel quick-panel"><div className="panel-head"><div><div className="panel-icon purple-icon"><Command size={17}/></div><div><h3>Quick actions</h3><p>Jump straight into common tasks</p></div></div></div><div className="quick-actions">
            <QuickAction icon={Shield} title="Moderation tools" desc="Review actions and cases" onClick={() => choose('Moderation')}/>
            <QuickAction icon={MessageSquare} title="Welcome messages" desc="Configure greeting flow" onClick={() => choose('Welcome')}/>
            <QuickAction icon={SlidersHorizontal} title="Server settings" desc="Tune module preferences" onClick={() => choose('Settings')}/>
            <QuickAction icon={Terminal} title="Bot diagnostics" desc="Check service health" onClick={() => notify('Diagnostics require the backend API.')}/>
          </div></div>
          <div className="panel setup-panel"><div className="panel-head"><div><div className="panel-icon orange-icon"><Sparkles size={17}/></div><div><h3>Get started</h3><p>Bring your control center online</p></div></div></div><div className="setup-steps">
            <SetupStep done title="Dashboard interface" desc="Responsive UI scaffold is ready"/>
            <SetupStep title="Discord OAuth" desc="Add client ID, secret and callback URL"/>
            <SetupStep title="Live bot data" desc="Connect a protected API to the bot database"/>
          </div><button className="primary-wide" onClick={() => setShowConnect(true)}>Configure Discord connection <ExternalLink size={14}/></button></div>
        </section>
        <footer className="footer"><div><div className="footer-mark">F</div><span>FALLEN <i>CONTROL CENTER</i></span></div><span>Built for calm, deliberate control.</span><a href="https://github.com/NOAH-NULL/FALLEN" target="_blank" rel="noreferrer">Repository <ExternalLink size={12}/></a></footer>
      </div>
    </main>

    {showConnect && <div className="modal-backdrop" onClick={() => setShowConnect(false)}><div className="connect-modal" onClick={e => e.stopPropagation()}><button className="modal-close icon-button" onClick={() => setShowConnect(false)} aria-label="Close dialog"><X size={18}/></button><div className="modal-emblem"><Bot size={25}/></div><div className="eyebrow">FALLEN AUTHENTICATION</div><h2>Connect your Discord</h2><p>Discord OAuth is not configured in this deployment yet. Set up the API environment first, then enable the sign-in flow.</p><div className="requirements"><div><Check size={15}/> Discord application client ID</div><div><Check size={15}/> OAuth client secret stored server-side</div><div><Check size={15}/> Exact callback URL registered in Discord</div><div><Check size={15}/> HTTPS and a strong session secret</div></div><button className="primary-wide" onClick={() => { setShowConnect(false); notify('See control-center/README.md for setup steps.'); }}>Got it <ChevronRight size={15}/></button><a href="https://discord.com/developers/applications" target="_blank" rel="noreferrer">Open Discord Developer Portal <ExternalLink size={12}/></a></div></div>}
    {toast && <div className="toast"><CircleHelp size={16}/>{toast}</div>}
  </div>;
}

function StatCard({icon: Icon, label, value, note, color}) {
  return <article className="stat-card"><div className="stat-top"><span>{label}</span><div className={'stat-icon '+color}><Icon size={17}/></div></div><div className="stat-value">{value}</div><div className="stat-note"><span className="muted-dot"/>{note}</div></article>;
}
function ToggleRow({title, desc, enabled, onClick}) {
  return <div className="toggle-row"><div><strong>{title}</strong><span>{desc}</span></div><button className={'toggle '+(enabled?'on':'')} onClick={onClick} aria-label={'Toggle '+title} aria-pressed={enabled}><i/></button></div>;
}
function EventRow({event, last}) {
  const Icon = event.type === 'shield' ? ShieldCheck : event.type === 'users' ? Users : event.type === 'message' ? MessageSquare : Settings2;
  return <div className={'event-row '+(last?'last':'')}><div className={'event-icon '+event.tone}><Icon size={15}/></div><div className="event-copy"><strong>{event.title}</strong><span>{event.detail}</span></div><time>{event.time}</time></div>;
}
function QuickAction({icon: Icon, title, desc, onClick}) {
  return <button className="quick-action" onClick={onClick}><div className="quick-action-icon"><Icon size={16}/></div><div><strong>{title}</strong><span>{desc}</span></div><ChevronRight size={15}/></button>;
}
function SetupStep({done, title, desc}) {
  return <div className="setup-step"><span className={'step-check '+(done?'done':'')}>{done?<Check size={13}/>:<span/>}</span><div><strong>{title}</strong><span>{desc}</span></div><span className={'step-state '+(done?'complete':'')}>{done?'READY':'TODO'}</span></div>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);