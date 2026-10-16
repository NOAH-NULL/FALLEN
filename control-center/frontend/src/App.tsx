import { useState } from "react";
import {
  Activity, AudioWaveform, Bot, ChartNoAxesCombined, ChevronDown,
  CircleHelp, Command, Gauge, LayoutDashboard, LockKeyhole, Menu,
  MessageSquareText, ScrollText, Server, Settings2, ShieldCheck,
  Sparkles, Users, X
} from "lucide-react";

type Section = "Overview" | "Servers" | "Moderation" | "Leveling" | "Welcome" | "Analytics" | "Logs" | "Settings";

const navigation: { label: Section; icon: typeof LayoutDashboard }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Servers", icon: Server },
  { label: "Moderation", icon: ShieldCheck },
  { label: "Leveling", icon: Sparkles },
  { label: "Welcome", icon: MessageSquareText },
  { label: "Analytics", icon: ChartNoAxesCombined },
  { label: "Logs", icon: ScrollText },
  { label: "Settings", icon: Settings2 }
];

const demoActivity = [
  { icon: ShieldCheck, color: "violet", title: "Moderation module", detail: "Demo activity · no live event feed connected", time: "Example" },
  { icon: Users, color: "blue", title: "Member event", detail: "Illustrative activity item", time: "Example" },
  { icon: MessageSquareText, color: "green", title: "Welcome module", detail: "Waiting for backend integration", time: "Pending" }
];

function App() {
  const [section, setSection] = useState<Section>("Overview");
  const [serverOpen, setServerOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState("Demo mode · No production bot connection");

  function chooseSection(next: Section) {
    setSection(next);
    setMobileNav(false);
    if (next !== "Overview") setNotice(`${next} is a UI scaffold. Live data and write actions are not connected yet.`);
    else setNotice("Demo mode · No production bot connection");
  }

  return (
    <div className="app-shell">
      {mobileNav && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand"><div className="brand-mark"><Bot size={22} /></div><div><strong>FALLEN</strong><span>CONTROL CENTER</span></div><button className="mobile-close icon-button" aria-label="Close menu" onClick={() => setMobileNav(false)}><X size={18}/></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ label, icon: Icon }) => (
            <button key={label} className={`nav-item ${section === label ? "active" : ""}`} onClick={() => chooseSection(label)}>
              <Icon size={17} /><span>{label}</span>{label === "Logs" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom"><div className="bot-avatar"><Bot size={18}/></div><div className="bot-meta"><strong>FALLEN Bot</strong><span><i className="status-dot" /> Status not connected</span></div><button className="icon-button" aria-label="Help" onClick={() => setNotice("Help: connect and authenticate the backend before enabling live controls.")}><CircleHelp size={17}/></button></div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setMobileNav(true)}><Menu size={20}/></button>
          <div className="breadcrumbs">Control Center <span>/</span> <strong>{section}</strong></div>
          <div className="topbar-right"><span className="environment-pill"><i/> DEMO ENVIRONMENT</span><button className="profile-button" onClick={() => setNotice("Discord sign-in has not been implemented yet.")}><div className="profile-avatar">N</div><span>Guest</span><ChevronDown size={15}/></button></div>
        </header>

        <div className="page-wrap">
          <div className="notice"><Activity size={16}/><span>{notice}</span></div>
          <section className="welcome-row"><div><div className="eyebrow">COMMAND CENTER</div><h1>{section === "Overview" ? "Your community, in control." : section}</h1><p>Manage FALLEN from one calm, focused workspace.</p></div><button className="server-picker" onClick={() => setServerOpen(!serverOpen)}><span className="server-icon"><Server size={17}/></span><span><small>SELECTED SERVER</small><strong>Demo community</strong></span><ChevronDown size={16}/></button></section>
          {serverOpen && <div className="server-menu"><strong>Demo community</strong><p>This is a placeholder. Server discovery will use Discord OAuth and verified bot membership.</p><button onClick={() => { setServerOpen(false); setNotice("Server selection is not connected to Discord yet."); }}>Got it</button></div>}

          {section === "Overview" ? <>
            <div className="metrics-grid">
              <Metric icon={Server} label="Connected servers" value="—" foot="Awaiting live API" tone="violet"/>
              <Metric icon={Users} label="Community members" value="—" foot="Awaiting live API" tone="blue"/>
              <Metric icon={Command} label="Commands today" value="—" foot="Awaiting event data" tone="green"/>
              <Metric icon={Gauge} label="Bot latency" value="—" foot="Not connected" tone="amber"/>
            </div>
            <div className="content-grid">
              <section className="panel chart-panel"><div className="panel-heading"><div><h2>Activity overview</h2><p>Metrics will appear when telemetry is connected.</p></div><span className="subtle-chip">No data</span></div><div className="chart-empty"><div className="chart-icon"><ChartNoAxesCombined size={26}/></div><strong>Waiting for real telemetry</strong><span>We won't invent usage numbers or chart fake activity.</span><div className="chart-lines"><i/><i/><i/><i/><i/><i/><i/></div></div></section>
              <section className="panel activity-panel"><div className="panel-heading"><div><h2>Recent activity</h2><p>Illustrative placeholders only</p></div><Activity size={18} className="muted-icon"/></div><div className="activity-list">{demoActivity.map(({icon: Icon,color,title,detail,time})=><div className="activity-item" key={title}><div className={`activity-icon ${color}`}><Icon size={16}/></div><div className="activity-copy"><strong>{title}</strong><span>{detail}</span></div><small>{time}</small></div>)}</div></section>
            </div>
            <section className="panel modules-panel"><div className="panel-heading"><div><h2>Control modules</h2><p>Feature areas planned for the first release.</p></div><span className="subtle-chip">Scaffold</span></div><div className="module-grid"><Module icon={ShieldCheck} title="Moderation" text="Review actions and audit trails."/><Module icon={Sparkles} title="Leveling" text="XP, cooldowns and level rewards."/><Module icon={MessageSquareText} title="Welcome" text="Join, leave and message templates."/><Module icon={LockKeyhole} title="Security" text="Access controls and safe operations."/></div></section>
          </> : <section className="panel placeholder-page"><div className="placeholder-icon"><Settings2 size={25}/></div><h2>{section} module</h2><p>This screen is part of the initial UI scaffold. It will be connected only after its API contract, permissions, and tests are implemented.</p><button className="primary-button" onClick={() => chooseSection("Overview")}>Return to overview</button></section>}
          <footer><span><Bot size={14}/> FALLEN Control Center</span><span>Scaffold build · No live bot access</span></footer>
        </div>
      </main>
    </div>
  );
}

function Metric({ icon: Icon, label, value, foot, tone }: { icon: typeof Server; label: string; value: string; foot: string; tone: string }) {
  return <section className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={18}/></div><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong><span className="metric-foot">{foot}</span></section>;
}

function Module({ icon: Icon, title, text }: { icon: typeof Server; title: string; text: string }) {
  return <div className="module-card"><div className="module-icon"><Icon size={18}/></div><div><strong>{title}</strong><p>{text}</p></div></div>;
}

export default App;
