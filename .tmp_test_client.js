
    (function(){
      try{
      console.debug('[test-client] script loaded');
      let token = null;
      let sock = null;
      let currentUserDisplay = 'Guest';

      const el = id => document.getElementById(id);
      const loginPhone = el('login-phone');
      const loginPass = el('login-pass');
      const btnLogin = el('btn-login');
      const btnLogout = el('btn-logout');
      const loginStatus = el('login-status');

      // Startup presence debug to detect missing elements that would stop script
      console.debug('[test-client] element presence', {
        loginPhone: !!loginPhone,
        loginPass: !!loginPass,
        btnLogin: !!btnLogin,
        btnLogout: !!btnLogout,
      });

  const btnCreateRoom = el('btn-create-room');
  const roomParticipants = el('room-participants');
  const roomPrivate = el('room-private');
  const roomResult = el('room-result');
  const btnConnect = el('btn-connect');
  const roomIdInput = el('room-id');
  const roomOtherName = el('room-other-name');
  const btnDisconnect = el('btn-disconnect');
  const roomAvatar = el('room-avatar');
  const roomHeaderName = el('room-header-name');

      const wsStatus = el('ws-status');

      const messages = el('messages');
      const msgText = el('msg-text');
      const btnSend = el('btn-send');
      const userNameEl = el('user-name');

  function timeNow(){ const dt = new Date(); return dt.getHours().toString().padStart(2,'0')+':'+dt.getMinutes().toString().padStart(2,'0'); }
  function addMessage(who, txt, attrs){
    try{
      if(!messages){ console.warn('[test-client] messages element missing, fallback to console'); console.log(who, txt, attrs); return null; }
      const d = document.createElement('div'); d.className='msg other'; if(who==='me') d.className='msg me';
      const bubble = document.createElement('div'); bubble.className='bubble';
      const ts = attrs && attrs.ts? attrs.ts : timeNow();
      bubble.innerHTML = '<div style="font-size:12px;color:#374151;margin-bottom:6px"><b>'+(who)+'</b></div><div>'+txt+'</div><div class="meta" style="text-align:right;margin-top:6px">'+ts+'</div>';
      if(attrs && attrs.client_msg_id) d.setAttribute('data-client-msg-id', attrs.client_msg_id);
      d.appendChild(bubble);
      messages.appendChild(d);
      messages.scrollTop = messages.scrollHeight;
      return d;
    }catch(e){ console.error('[test-client] addMessage failed', e); console.log(who, txt, attrs); return null; }
  }

      if (btnLogin) btnLogin.addEventListener('click', async ()=>{
        const phone = (loginPhone.value||'').trim();
        const password = loginPass.value||'';
        if (!phone) { loginStatus.textContent='phone_number required'; addMessage('system','phone_number required'); return; }
        try{
          console.debug('[test-client] login ->', { phone });
          const res = await fetch('/api/auth/login/', { method:'POST', headers: { 'Content-Type':'application/json' }, body: JSON.stringify({ phone_number: phone, password: password }) });
          console.debug('[test-client] login response status', res.status);
          const bodyText = await res.text();
          console.debug('[test-client] login response body', bodyText);
          if (!res.ok) { loginStatus.textContent = 'Login failed: '+res.status; addMessage('system', bodyText); return; }
          const data = JSON.parse(bodyText);
          token = (data.token||'').trim();
          if(loginStatus) loginStatus.textContent = token?('Logged in'):'Logged in';
          // show name in header if available
          currentUserDisplay = (data.user && (data.user.full_name || data.user.username || data.user.phone_number)) || (data.user && data.user.phone_number) || 'Me';
          if(userNameEl) userNameEl.textContent = currentUserDisplay;
          addMessage('system','login OK');
        }catch(e){ loginStatus.textContent = 'Login error'; addMessage('system','login error: '+e.message); }
  });

  if (btnLogout) btnLogout.addEventListener('click', ()=>{ token = null; loginStatus.textContent='Logged out'; addMessage('system','logged out'); userNameEl.textContent = 'Guest'; });

      if (btnCreateRoom) btnCreateRoom.addEventListener('click', async ()=>{
        if (!token) return addMessage('system','login first');
        const raw = (roomParticipants.value||'').trim();
        const participants = raw? raw.split(',').map(x=>parseInt(x.trim())).filter(Boolean) : [];
        if (roomPrivate.checked && participants.length !== 2) { addMessage('system','Private rooms require exactly 2 participant ids'); return; }
        const payload = { participants: participants, is_private: roomPrivate.checked };
        try{
          console.debug('[test-client] create-room payload', payload);
          const res = await fetch('/api/chat/rooms/', { method:'POST', headers: { 'Content-Type':'application/json', 'Authorization':'Token '+token }, body: JSON.stringify(payload) });
          console.debug('[test-client] create-room status', res.status);
          const txt = await res.text();
          console.debug('[test-client] create-room body', txt);
          if (!res.ok) { addMessage('system','create room failed: '+res.status); addMessage('system', txt); return; }
          const data = JSON.parse(txt);
          if(roomResult) roomResult.textContent = JSON.stringify(data);
          addMessage('system','room created: '+data.id);
        }catch(e){ addMessage('system','create room error: '+e.message); }
  });

      function wsUrlForRoom(room){ const proto = location.protocol==='https:'?'wss':'ws'; const raw = token||''; const q = raw?('?token='+encodeURIComponent(raw)) : ''; return proto+'://'+location.host+'/ws/chat/'+encodeURIComponent(room)+'/'+q; }

      if (btnSend) btnSend.addEventListener('click', ()=>{
        if (!sock || sock.readyState!==WebSocket.OPEN) return addMessage('system','socket not open');
        const client_msg_id = 'cmsg_'+Date.now()+'_'+Math.floor(Math.random()*10000);
        const payload = { content: (msgText.value||'').trim(), client_msg_id };
        try{ sock.send(JSON.stringify(payload)); }catch(e){ addMessage('system','send failed: '+e.message); return; }
        // optimistic local echo with data-client-msg-id so we can correlate later
        const node = addMessage('me', payload.content, { client_msg_id, ts: timeNow() });
        msgText.value='';
      });

  // connect helpers
  function setRoomHeader(name){ try{ roomOtherName.textContent = name; roomHeaderName.textContent = name; const initials = (name||'').split(' ').map(x=>x[0]).filter(Boolean).slice(0,2).join('').toUpperCase() || '?'; roomAvatar.textContent = initials; }catch(e){} }

  function connectToRoom(room){ if(!token) return addMessage('system','login first'); const url = wsUrlForRoom(room); addMessage('system','connecting to '+url); try{ sock = new WebSocket(url); }catch(e){ addMessage('system','ws ctor failed: '+e.message); return; } sock.onopen = ()=>{ wsStatus.textContent='OPEN'; addMessage('system','ws open'); console.debug('[test-client] ws open'); }; sock.onmessage = (ev)=>{ console.debug('[test-client] ws message', ev.data); try{ const d = JSON.parse(ev.data); if(d.client_msg_id){ const local = messages.querySelector('[data-client-msg-id="'+d.client_msg_id+'"]'); if(local){ local.classList.remove('me'); local.classList.add('other'); const bubble = local.querySelector('.bubble'); if(bubble) bubble.innerHTML = '<div style="font-size:12px;color:#374151;margin-bottom:6px"><b>'+(d.username||'recv')+'</b></div><div>'+(d.message||'')+'</div><div class="meta" style="text-align:right;margin-top:6px">'+(d.timestamp||timeNow())+'</div>'; local.removeAttribute('data-client-msg-id'); messages.scrollTop = messages.scrollHeight; setRoomHeader(d.username||roomOtherName.textContent||'(no one)'); return; } } // fallback dedupe: find last local 'me' with same text const serverText = (d.message||ev.data)+'', serverUser = d.username||'recv'; const meNodes = Array.from(messages.querySelectorAll('.msg')).filter(n=>n.classList.contains('me')).reverse(); let replaced = false; for(const node of meNodes){ const bubble = node.querySelector('.bubble'); const text = bubble? bubble.innerText.trim() : node.innerText.replace(/^me:\s*/,'').trim(); if(text === serverText){ node.classList.remove('me'); node.classList.add('other'); const bubble2 = node.querySelector('.bubble'); if(bubble2) bubble2.innerHTML = '<div style="font-size:12px;color:#374151;margin-bottom:6px"><b>'+serverUser+'</b></div><div>'+serverText+'</div><div class="meta" style="text-align:right;margin-top:6px">'+(d.timestamp||timeNow())+'</div>'; replaced=true; setRoomHeader(serverUser); break; } } if(!replaced) addMessage(d.username||'recv', d.message||ev.data, { ts: d.timestamp || timeNow() }); setRoomHeader(d.username||roomOtherName.textContent||'(no one)'); }catch(e){ addMessage('recv', ev.data); } }; sock.onclose = (ev)=>{ wsStatus.textContent='CLOSED'; addMessage('system','ws close: code='+ev.code+' reason='+ev.reason); console.debug('[test-client] ws close', ev); sock=null; }; sock.onerror = (e)=>{ addMessage('system','ws error (see server logs)'); console.debug('[test-client] ws error', e); }; }

  if (btnConnect) btnConnect.addEventListener('click', ()=>{ const room = (roomIdInput.value||'11').trim(); if(!room) return addMessage('system','enter room id'); connectToRoom(room); });

  if (btnDisconnect) btnDisconnect.addEventListener('click', ()=>{ if(sock){ try{ sock.close(); }catch(e){} } else { addMessage('system','not connected'); } });

  // messages dblclick helper
  if (messages) messages.addEventListener('dblclick', ()=>{ if(!sock) addMessage('system','Double-click here to open WS via Connect button'); });

  // open connection via prompt for room id
  document.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && (e.target===msgText)) { if (btnSend) btnSend.click(); } });

      // Quick connect button on the header area
      // For simplicity, reuse login button to open ws after login
      if (btnLogin) btnLogin.addEventListener('dblclick', ()=>{
        if(!token) return addMessage('system','login first');
        const room = prompt('Enter room id', '11') || '11';
        const url = wsUrlForRoom(room);
        addMessage('system','connecting to '+url);
        try{ sock = new WebSocket(url); }catch(e){ addMessage('system','ws ctor failed: '+e.message); return; }
  sock.onopen = ()=>{ if(wsStatus) wsStatus.textContent='OPEN'; addMessage('system','ws open'); console.debug('[test-client] ws open'); };
        sock.onmessage = (ev)=>{ console.debug('[test-client] ws message', ev.data); try{ const d = JSON.parse(ev.data);
            if(d.client_msg_id){
              const local = messages.querySelector('[data-client-msg-id="'+d.client_msg_id+'"]');
              if(local){
                local.classList.remove('me'); local.classList.add('other');
                const bubble = local.querySelector('.bubble'); if(bubble) bubble.innerHTML = '<div style="font-size:12px;color:#374151;margin-bottom:6px"><b>'+(d.username||'recv')+'</b></div><div>'+(d.message||'')+'</div><div class="meta" style="text-align:right;margin-top:6px">'+(d.timestamp||timeNow())+'</div>';
                local.removeAttribute('data-client-msg-id');
                messages.scrollTop = messages.scrollHeight; return;
              }
            }
            // fallback dedupe: find last local 'me' with same text
            const serverText = (d.message||ev.data)+'', serverUser = d.username||'recv';
            const meNodes = Array.from(messages.querySelectorAll('.msg')).filter(n=>n.classList.contains('me')).reverse();
            let replaced = false;
            for(const node of meNodes){
              const bubble = node.querySelector('.bubble'); const text = bubble? bubble.innerText.trim() : node.innerText.replace(/^me:\s*/,'').trim();
              if(text === serverText){ node.classList.remove('me'); node.classList.add('other'); const bubble2 = node.querySelector('.bubble'); if(bubble2) bubble2.innerHTML = '<b>'+serverUser+'</b><div style="margin-top:6px">'+serverText+'</div>'; replaced=true; break; }
            }
        if(!replaced) addMessage(d.username||'recv', d.message||ev.data, { ts: d.timestamp || timeNow() });
        // update other participant display if different from current user
        try{ if(d.username && d.username !== currentUserDisplay){ roomOtherName.textContent = d.username; } }catch(e){}
         }catch(e){ addMessage('recv', ev.data); } };
        sock.onclose = (ev)=>{ wsStatus.textContent='CLOSED'; addMessage('system','ws close: code='+ev.code+' reason='+ev.reason); console.debug('[test-client] ws close', ev); sock=null; };
        sock.onerror = (e)=>{ addMessage('system','ws error (see server logs)'); console.debug('[test-client] ws error', e); };
      });

      }catch(err){
        console.error('[test-client] fatal script error', err);
        try{ if(window && window.alert) window.alert('Test client script error: '+(err&&err.message)); }catch(e){}
      }
    })();
    