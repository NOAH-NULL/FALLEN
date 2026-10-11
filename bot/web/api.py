from aiohttp import web
import json

DASHBOARD_HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fallen • Command Center</title><style>
:root{color-scheme:dark;--bg:#07080c;--panel:#10131b;--line:#242936;--text:#f5f7fb;--muted:#8f96a6;--accent:#8b5cf6;--good:#43e6a1;--bad:#ff667d}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#21143c 0,#07080c 44%);font:15px Inter,system-ui,sans-serif;color:var(--text)}main{max-width:1180px;margin:auto;padding:46px 22px}.brand{letter-spacing:.24em;font-size:11px;font-weight:900;color:#c4b5fd}.hero{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:10px 0 28px}.hero h1{font-size:44px;margin:0}.hero p{color:var(--muted);margin:8px 0 0}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{background:rgba(16,19,27,.88);border:1px solid var(--line);border-radius:18px;padding:19px;box-shadow:0 14px 44px #0005}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.13em}.value{font-size:27px;font-weight:850;margin-top:7px}.wide{margin-top:12px}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.status{display:flex;align-items:center;gap:8px}.dot{width:9px;height:9px;border-radius:50%;background:var(--good);box-shadow:0 0 15px var(--good)}input,select{width:100%;padding:11px 12px;background:#0a0c11;color:var(--text);border:1px solid var(--line);border-radius:10px;margin-top:9px}button{padding:10px 13px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-weight:800;cursor:pointer;margin-top:9px}.muted{color:var(--muted)}pre{white-space:pre-wrap;color:#cbd1dc;font-size:12px;max-height:260px;overflow:auto}#error{color:var(--bad);min-height:20px;margin-top:9px}@media(max-width:760px){.grid{grid-template-columns:1fr 1fr}.row{grid-template-columns:1fr}.hero{display:block}.hero h1{font-size:34px}}@media(max-width:440px){.grid{grid-template-columns:1fr}}
</style></head><body><main><div class="brand">F A L L E N</div><section class="hero"><div><h1>Command center.</h1><p>Security, moderation and recovery control plane.</p></div><div class="status"><span class="dot"></span><span id="state">Authentication required</span></div></section>
<div class="grid"><div class="card"><div class="label">Guilds</div><div class="value" id="guilds">—</div></div><div class="card"><div class="label">Members</div><div class="value" id="users">—</div></div><div class="card"><div class="label">Shards</div><div class="value" id="shards">—</div></div><div class="card"><div class="label">Latency</div><div class="value" id="latency">—</div></div></div>
<section class="card wide"><div class="label">Control plane access</div><div class="muted" style="margin-top:7px">Use the configured dashboard credential. It remains in this browser session only.</div><input id="key" type="password" placeholder="Dashboard credential"><input id="guild" placeholder="Guild ID"><button onclick="loadGuild()">Open Guild</button><div id="error"></div></section>
<div class="row wide"><section class="card"><div class="label">Security audit</div><pre id="audit">Connect a guild to inspect recent security events.</pre></section><section class="card"><div class="label">Snapshots</div><pre id="snapshots">Connect a guild to inspect recovery snapshots.</pre></section></div>
</main><script>
const keyEl=document.getElementById('key');keyEl.value=sessionStorage.getItem('fallen_key')||'';function headers(){return {'Authorization':'Bearer '+keyEl.value,'X-Dashboard-Key':keyEl.value}}async function req(url,opt={}){const r=await fetch(url,{...opt,headers:{...headers(),...(opt.headers||{})}});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}async function loadGuild(){const e=document.getElementById('error');e.textContent='';sessionStorage.setItem('fallen_key',keyEl.value);try{const s=await req('/api/stats');document.getElementById('guilds').textContent=s.guilds;document.getElementById('users').textContent=s.users;document.getElementById('shards').textContent=s.shards;document.getElementById('latency').textContent=(s.latency_ms??0)+' ms';const g=document.getElementById('guild').value.trim();if(!g)throw Error('Enter a guild ID.');const [a,ss]=await Promise.all([req('/api/v1/guilds/'+g+'/audit-logs'),req('/api/v1/guilds/'+g+'/snapshots')]);document.getElementById('audit').textContent=JSON.stringify(a,null,2);document.getElementById('snapshots').textContent=JSON.stringify(ss,null,2);document.getElementById('state').textContent='Operational'}catch(x){e.textContent=x.message;document.getElementById('state').textContent='Connection failed'}}
</script></body></html>'''

class DashboardAPI:
    def __init__(self,bot,host='0.0.0.0',port=8080):
        self.bot=bot; self.host=host; self.port=port; self.runner=None

    def _authorized(self, request):
        configured=self.bot.settings.dashboard_api_key
        if not configured: return False
        bearer=request.headers.get('Authorization','')
        supplied=request.headers.get('X-Dashboard-Key','')
        return supplied == configured or bearer == f'Bearer {configured}'

    def _guild(self, guild_id):
        try: gid=int(guild_id)
        except (TypeError,ValueError): return None
        return self.bot.get_guild(gid)

    def _guard(self, request, guild_id=None):
        if not self._authorized(request): return web.json_response({'error':'unauthorized'},status=401)
        if guild_id is not None and not self._guild(guild_id): return web.json_response({'error':'guild not managed by this bot'},status=404)
        return None

    async def start(self):
        app=web.Application(client_max_size=2*1024*1024)
        app.add_routes([
            web.get('/',self.dashboard), web.get('/dashboard',self.dashboard),
            web.get('/api/health',self.health), web.get('/api/stats',self.stats),
            web.get('/api/v1/guilds/{guild_id}/audit-logs',self.audit_logs),
            web.get('/api/v1/guilds/{guild_id}/snapshots',self.snapshots),
            web.post('/api/v1/guilds/{guild_id}/snapshots/restore',self.restore_snapshot),
            web.patch('/api/v1/guilds/{guild_id}/automod/rules',self.patch_automod),
        ])
        self.runner=web.AppRunner(app); await self.runner.setup(); site=web.TCPSite(self.runner,self.host,self.port); await site.start()

    async def dashboard(self,r): return web.Response(text=DASHBOARD_HTML,content_type='text/html')
    async def health(self,r): return web.json_response({'ok':True,'guilds':len(self.bot.guilds),'latency_ms':round(self.bot.latency*1000,2)})
    async def stats(self,r):
        guard=self._guard(r)
        if guard:return guard
        return web.json_response({'guilds':len(self.bot.guilds),'users':sum(g.member_count or 0 for g in self.bot.guilds),'shards':self.bot.shard_count,'latency_ms':round(self.bot.latency*1000,2)})

    async def audit_logs(self,r):
        guard=self._guard(r,r.match_info['guild_id']);
        if guard:return guard
        try: limit=min(100,max(1,int(r.query.get('limit','25'))))
        except ValueError: limit=25
        rows=await self.bot.extreme.security_events(int(r.match_info['guild_id']),limit)
        return web.json_response({'items':[{'id':x.id,'event_type':x.event_type,'actor_id':x.actor_id,'target_id':x.target_id,'details':x.details,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]})

    async def snapshots(self,r):
        guard=self._guard(r,r.match_info['guild_id']);
        if guard:return guard
        rows=await self.bot.extreme.snapshots(int(r.match_info['guild_id']))
        return web.json_response({'items':[{'id':x.id,'name':x.name,'created_by':x.created_by,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]})

    async def restore_snapshot(self, r):
        raw_gid = r.match_info['guild_id']
        guard = self._guard(r, raw_gid)
        if guard:
            return guard
        gid = int(raw_gid)
        try:
            body = await r.json()
        except Exception:
            return web.json_response({'error': 'invalid JSON'}, status=400)
        if not isinstance(body, dict):
            return web.json_response({'error': 'JSON body must be an object'}, status=400)
        name = str(body.get('name', '')).strip()
        if not name or len(name) > 64:
            return web.json_response({'error': 'snapshot name is required (1–64 characters)'}, status=400)
        guild = self.bot.get_guild(gid)
        if name == '__security_state__':
            result = await self.bot.restore_security_state(guild, name)
        elif name.startswith('__'):
            return web.json_response({'error': 'reserved recovery snapshots cannot be restored through this endpoint'}, status=400)
        else:
            snap = await self.bot.extreme.snapshot_get(gid, name)
            if not snap:
                return web.json_response({'error': 'snapshot not found'}, status=404)
            try:
                result = await self.bot.extreme.restore_features(
                    gid,
                    snap.payload.get('features', {}),
                )
            except ValueError as exc:
                return web.json_response({'error': str(exc)}, status=400)
            result = {'snapshot': name, **result}
        await self.bot.extreme.record_security(
            gid,
            'dashboard_snapshot_restore',
            details={'name': name, 'result': result},
        )
        return web.json_response({'ok': True, 'result': result})

    async def patch_automod(self,r):
        gid=int(r.match_info['guild_id']); guard=self._guard(r,gid)
        if guard:return guard
        try: body=await r.json()
        except Exception:return web.json_response({'error':'invalid JSON'},status=400)
        try:
            config=await self.bot.automod.configure_heat(gid, **body)
        except (TypeError,ValueError) as exc:
            return web.json_response({'error':str(exc)},status=400)
        await self.bot.extreme.record_security(gid,'dashboard_automod_update',details={'changes':body})
        return web.json_response({'ok':True,'config':config})

    async def close(self):
        if self.runner: await self.runner.cleanup()
