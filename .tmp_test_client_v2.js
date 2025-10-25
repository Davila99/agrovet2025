(function(){
  function qs(id){ return document.getElementById(id); }
  function timeNow(){ const dt = new Date(); return dt.getHours().toString().padStart(2,'0')+':'+dt.getMinutes().toString().padStart(2,'0'); }
  function safeText(node, text){ if(!node) return; node.textContent = text; }
  function initClient(){
    let token=null; let sock=null;
    const loginPhone = qs('login-phone');
    const loginPass = qs('login-pass');
    const btnLogin = qs('btn-login');
    const btnLogout = qs('btn-logout');
    const loginStatus = qs('login-status');
    const btnCreateRoom = qs('btn-create-room');
    const roomParticipants = qs('room-participants');
    const roomPrivate = qs('room-private');
    const roomResult = qs('room-result');
    const btnConnect = qs('btn-connect');
    const roomIdInput = qs('room-id');
    const roomOtherName = qs('room-other-name');
    const btnDisconnect = qs('btn-disconnect');
    const roomAvatar = qs('room-avatar');
    const roomHeaderName = qs('room-header-name');
    const wsStatus = qs('ws-status');
    const messages = qs('messages');
    const msgText = qs('msg-text');
    const btnSend = qs('btn-send');
    const userNameEl = qs('user-name');
    function addMessage(who, text, opts){ if(!messages) return; const row=document.createElement('div'); row.className = who==='me'?'msg me':'msg other'; const bubble=document.createElement('div'); bubble.className='bubble'; const ts=(opts&&opts.ts)?opts.ts:timeNow(); bubble.innerHTML='<div style="font-size:12px;color:#374151;margin-bottom:6px"><b>'+(who)+'</b></div><div>'+(text||'')+'</div><div class="meta" style="text-align:right;margin-top:6px">'+ts+'</div>'; if(opts&&opts.client_msg_id) row.setAttribute('data-client-msg-id', opts.client_msg_id); row.appendChild(bubble); messages.appendChild(row); messages.scrollTop=messages.scrollHeight; }
    function wsUrlForRoom(room){ const proto = location.protocol==='https:'?'wss':'ws'; const q = token?('?token='+encodeURIComponent(token)) : ''; return proto+'://'+location.host+'/ws/chat/'+encodeURIComponent(room)+'/'+q; }
    function setRoomHeader(name){ try{ if(roomOtherName) roomOtherName.textContent = name||'(no one)'; if(roomHeaderName) roomHeaderName.textContent = name||'(no one)'; if(roomAvatar) roomAvatar.textContent = (name||'?').split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase(); }catch(e){} }
    function openSocket(room){ if(!token){ addMessage('system','login first'); return; } const url = wsUrlForRoom(room); addMessage('system','connecting to '+url); try{ sock=new WebSocket(url); }catch(e){ addMessage('system','ws ctor failed'); return; } if(wsStatus) wsStatus.textContent='CONNECTING'; sock.onopen=()=>{ if(wsStatus) wsStatus.textContent='OPEN'; addMessage('system','ws open'); }; sock.onmessage = ev=>{ try{ const d = JSON.parse(ev.data); if(d.client_msg_id){ const local = messages && messages.querySelector('[data-client-msg-id="'+d.client_msg_id+'"]'); if(local){ local.classList.remove('me'); local.classList.add('other'); const bubble = local.querySelector('.bubble'); if(bubble) bubble.innerHTML = '<div style="font-size:12px;color:#374151;margin-bottom:6px"><b>'+(d.username||'recv')+'</b></div><div>'+(d.message||'')+'</div><div class="meta" style="text-align:right;margin-top:6px">'+(d.timestamp||timeNow())+'</div>'; local.removeAttribute('data-client-msg-id'); messages.scrollTop = messages.scrollHeight; setRoomHeader(d.username||'(no one)'); return; } } addMessage(d.username||'recv', d.message||ev.data, { ts: d.timestamp || timeNow() }); setRoomHeader(d.username||'(no one)'); }catch(e){ addMessage('recv', ev.data); } }; sock.onclose = ev=>{ if(wsStatus) wsStatus.textContent='CLOSED'; addMessage('system','ws close: code='+ev.code+' reason='+(ev.reason||'')); sock=null; }; sock.onerror=e=>{ addMessage('system','ws error'); }; }
    if(btnLogin) btnLogin.addEventListener('click', async ()=>{ console.debug('login click'); const phone=(loginPhone&&loginPhone.value)||''; const password=(loginPass&&loginPass.value)||''; if(!phone){ if(loginStatus) loginStatus.textContent='phone_number required'; addMessage('system','phone_number required'); return; } try{ const res = await fetch('/api/auth/login/', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ phone_number: phone, password }) }); const txt = await res.text(); if(!res.ok){ addMessage('system','login failed: '+res.status); return; } const data = JSON.parse(txt); token = (data.token||'').trim(); safeText(loginStatus, token? 'Logged in':'Logged in'); safeText(userNameEl, (data.user && (data.user.full_name || data.user.phone_number))||'Me'); addMessage('system','login OK'); }catch(err){ console.error('login error', err); addMessage('system','login error'); } });
    if(btnLogout) btnLogout.addEventListener('click', ()=>{ token=null; safeText(loginStatus,'Logged out'); addMessage('system','logged out'); safeText(userNameEl,'Guest'); });
    if(btnCreateRoom) btnCreateRoom.addEventListener('click', async ()=>{ if(!token) return addMessage('system','login first'); const raw=(roomParticipants&&roomParticipants.value)||''; const participants= raw? raw.split(',').map(s=>parseInt(s.trim())).filter(Boolean):[]; const payload={ participants, is_private: !!(roomPrivate&&roomPrivate.checked) }; try{ const res=await fetch('/api/chat/rooms/',{ method:'POST', headers:{'Content-Type':'application/json','Authorization':'Token '+token}, body: JSON.stringify(payload)}); const txt=await res.text(); if(!res.ok){ addMessage('system','create room failed: '+res.status); return; } const data=JSON.parse(txt); if(roomResult) roomResult.textContent=JSON.stringify(data); addMessage('system','room created: '+(data.id||'(unknown)')); }catch(err){ console.error('create room error', err); addMessage('system','create room error'); } });
    if(btnConnect) btnConnect.addEventListener('click', ()=>{ const room=(roomIdInput&&roomIdInput.value)||'11'; if(!room) return addMessage('system','enter room id'); openSocket(room); });
    if(btnDisconnect) btnDisconnect.addEventListener('click', ()=>{ if(sock){ try{ sock.close(); }catch(e){} } else addMessage('system','not connected'); });
    if(btnSend) btnSend.addEventListener('click', ()=>{ if(!msgText) return; if(!sock||sock.readyState!==WebSocket.OPEN) return addMessage('system','socket not open'); const client_msg_id='cmsg_'+Date.now()+'_'+Math.floor(Math.random()*10000); const payload={ content: (msgText.value||'').trim(), client_msg_id }; try{ sock.send(JSON.stringify(payload)); }catch(e){ addMessage('system','send failed'); return; } addMessage('me', payload.content, { client_msg_id, ts: timeNow() }); msgText.value=''; });
    if(msgText) msgText.addEventListener('keydown', e=>{ if(e.key==='Enter'){ if(btnSend) btnSend.click(); } });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', initClient); else initClient();
})();
