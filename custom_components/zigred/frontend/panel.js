class ZigRedPanel extends HTMLElement {
  set hass(value) {
    this._hass = value;
    if (this.isConnected && this.shadowRoot && !this.readersLoaded) this.loadReaders();
  }
  connectedCallback() {
    if (!this.shadowRoot) this.build();
    if (this._hass) this.loadReaders();
    clearInterval(this.poll);
    this.poll = setInterval(() => { if (!document.hidden && !this.busy) this.loadReaders(); }, 2000);
  }
  build() {
    this.urls = []; this.readers = []; this.selectedId = null;
    const root = this.attachShadow({mode:'open'});
    root.innerHTML = `<style>
      :host{display:block;color:var(--primary-text-color,#172b42);font-family:var(--paper-font-body1_-_font-family,Arial,sans-serif);background:var(--primary-background-color,#f5f7fa);min-height:100%;--accent:#087ead;--soft:color-mix(in srgb,var(--accent) 9%,var(--card-background-color,#fff));}
      *{box-sizing:border-box} [hidden]{display:none!important} main{max-width:1260px;margin:auto;padding:36px 32px 64px} h1,h2,h3,p{margin:0} h1{font-size:30px;letter-spacing:-1px} h2{font-size:21px;letter-spacing:-.4px} h3{font-size:16px} p{line-height:1.6} .muted,small{color:var(--secondary-text-color,#63768b)} .eyebrow{font-size:11px;letter-spacing:1.5px;font-weight:700;color:var(--accent);text-transform:uppercase;margin-bottom:6px}
      header,.row,.section-head{display:flex;align-items:center;justify-content:space-between;gap:16px} .brand{display:flex;align-items:center;gap:14px} .brand img{width:56px;height:56px;object-fit:contain} .subtitle{margin-top:5px;font-size:14px} .header-actions{display:flex;gap:8px;flex-wrap:wrap}
      button,.link-button{font:inherit;font-size:13px;font-weight:600;cursor:pointer;min-height:40px;padding:10px 15px;border-radius:10px;border:1px solid var(--divider-color,#dce4ee);color:var(--primary-text-color);background:var(--card-background-color,#fff);text-decoration:none;display:inline-flex;gap:8px;align-items:center;justify-content:center} button:hover,.link-button:hover{border-color:var(--accent);background:var(--soft)} button.primary{background:var(--accent);color:#fff;border-color:var(--accent)} button.danger{color:#c44444} button:disabled{opacity:.5;cursor:wait} button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #43b7e0;outline-offset:2px} ha-icon{--mdc-icon-size:19px}
      .metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0} .metric{background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#dce4ee);border-radius:14px;padding:18px 22px} .metric strong{display:block;font-size:28px;margin-top:8px;letter-spacing:-1px} .metric span{font-size:12px;color:var(--secondary-text-color)}
      .workspace{display:grid;grid-template-columns:285px minmax(0,1fr);gap:24px;align-items:start} .card{background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#dce4ee);border-radius:18px;padding:24px;box-shadow:0 6px 24px #00142d05} aside .section-head{margin-bottom:16px} #readers{display:grid;gap:10px} .reader{width:100%;display:block;text-align:left;padding:16px;border-radius:12px} .reader.selected{border-color:var(--accent);background:var(--soft);box-shadow:inset 3px 0 var(--accent)} .reader strong{display:block;overflow-wrap:anywhere;font-size:14px;margin-bottom:7px} .reader small{display:block;font-weight:400;overflow-wrap:anywhere;font-size:11px} .reader .pill{margin-top:12px}
      .pill{display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:20px;font-size:11px;font-weight:600;background:var(--soft);color:var(--accent)} .pill.live{color:#12835c;background:color-mix(in srgb,#12835c 12%,var(--card-background-color,#fff))} .pill.paused{color:var(--secondary-text-color);background:var(--primary-background-color)} .dot{width:6px;height:6px;border-radius:50%;background:currentColor} .reader-meta{margin-top:6px;font-size:12px;overflow-wrap:anywhere} .live-box{margin:22px 0;background:var(--soft);border-radius:12px;padding:18px;display:grid;grid-template-columns:1fr 1fr;gap:18px} .live-box span{display:block;font-size:11px;color:var(--secondary-text-color);margin-bottom:7px} .live-box strong{font-size:15px;overflow-wrap:anywhere} code{font-family:monospace;font-size:12px;overflow-wrap:anywhere} .section-head{margin-bottom:16px} .section-head p{font-size:12px;margin-top:4px}
      .person{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:16px 0;border-bottom:1px solid var(--divider-color,#dce4ee)} .person:last-child{border-bottom:0} .person .identity{min-width:0} .person .identity strong{font-size:14px} .person small{display:block;font-size:11px;margin-top:6px} .person .actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end} .person .actions button{padding:7px 9px;min-height:34px;font-size:11px} .empty{text-align:center;padding:42px 16px;color:var(--secondary-text-color)} .empty ha-icon{--mdc-icon-size:36px;display:block;margin:0 auto 12px} .empty p{font-size:13px;margin-top:8px} .notice{padding:12px 16px;border-radius:10px;background:var(--soft);margin-top:16px;font-size:13px;line-height:1.5} .notice.error{color:#c44444;background:color-mix(in srgb,#c44444 8%,var(--card-background-color,#fff))}
      form{margin-top:20px;padding:20px;border:1px solid var(--accent);border-radius:12px;background:var(--soft)} label{display:block;font-size:12px;font-weight:600;margin:14px 0 6px} input,select{display:block;width:100%;padding:11px 12px;min-height:42px;border:1px solid var(--divider-color,#dce4ee);border-radius:8px;font:inherit;font-size:13px;background:var(--card-background-color,#fff);color:var(--primary-text-color)} .form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px} .form-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px} .pause-settings{display:flex;align-items:center;gap:10px;margin-top:16px} .pause-settings label{margin:0;font-weight:400} .pause-settings select{width:auto;max-width:230px} details{margin-top:24px;border-top:1px solid var(--divider-color);padding-top:20px} summary{cursor:pointer;font-size:13px;font-weight:600} details p{font-size:13px;margin:14px 0} .support{margin-top:24px} .support .card{padding:20px 24px} footer{margin-top:28px;font-size:12px} a{color:var(--accent)} #install{margin-top:12px}
      .install-progress progress{display:block;width:100%;height:8px;margin-top:12px;accent-color:var(--accent)}.install-progress.success{color:#12835c}.install-progress.success progress{accent-color:#12835c}
      .led-grid{display:grid;gap:10px;margin-top:18px}.led-row{display:grid;grid-template-columns:minmax(130px,1fr) 52px 120px;align-items:center;gap:12px;padding:12px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color)}.led-row label{display:flex;align-items:center;gap:9px;margin:0}.led-row input[type=checkbox]{width:18px;min-height:18px}.led-row input[type=color]{padding:3px;width:48px;height:40px}.led-row select{padding:8px}.led-tools{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}@media(max-width:450px){.led-row{grid-template-columns:1fr 48px}.led-row select{grid-column:1/-1}}
      @media(max-width:900px){main{padding:24px 18px}.workspace{grid-template-columns:230px minmax(0,1fr)}.card{padding:18px}.person{align-items:flex-start;flex-direction:column}.person .actions{justify-content:flex-start}} @media(max-width:650px){header{align-items:flex-start;flex-direction:column}.workspace{grid-template-columns:1fr}#readers{grid-template-columns:repeat(auto-fit,minmax(155px,1fr))}.metrics{gap:8px}.metric{padding:14px}.metric strong{font-size:24px}.form-grid,.live-box{grid-template-columns:1fr}.section-head{align-items:flex-start;flex-wrap:wrap}.pause-settings{align-items:flex-start;flex-direction:column}}
    </style><main>
      <header><div class="brand"><img src="/zigred_brand/icon.png?v=0.4.0" alt=""><div><div class="eyebrow">Espace lecteurs</div><h1>ZigRed</h1><p class="muted subtitle">Tes lecteurs, tes personnes. Tout au même endroit.</p></div></div>
      <div class="header-actions"><button id="refresh" aria-label="Actualiser les lecteurs"><ha-icon icon="mdi:refresh"></ha-icon>Actualiser</button><a class="link-button" href="/config/integrations/dashboard/add?domain=zigred"><ha-icon icon="mdi:plus"></ha-icon>Ajouter un lecteur</a></div></header>
      <div class="metrics"><div class="metric"><span>LECTEURS CONFIGURÉS</span><strong id="count-readers">—</strong></div><div class="metric"><span>ATTRIBUTIONS DE BADGES</span><strong id="count-people">—</strong></div><div class="metric"><span>LECTURES EN COURS</span><strong id="count-live">—</strong></div></div>
      <div id="page-status" class="notice" role="status" hidden></div>
      <div class="workspace"><aside class="card"><div class="section-head"><h3>Mes lecteurs</h3><ha-icon icon="mdi:access-point"></ha-icon></div><div id="readers"></div><p class="muted" style="font-size:11px;margin-top:16px">Appairage dans Zigbee2MQTT, puis association par adresse Zigbee. Les attributions restent propres à chaque lecteur.</p></aside>
      <div><div id="welcome" class="card empty"><ha-icon icon="mdi:nfc-variant"></ha-icon><h2>Bienvenue dans ZigRed</h2><p>Prépare ton lecteur en USB et installe le convertisseur ci-dessous. Appaire-le ensuite dans Zigbee2MQTT, puis clique sur Ajouter un lecteur pour le sélectionner.</p></div>
      <section id="detail" class="card" hidden><div class="section-head"><div><div class="eyebrow">Lecteur sélectionné</div><h2 id="reader-name"></h2><p id="reader-topic" class="muted reader-meta"></p></div><button id="rename-reader"><ha-icon icon="mdi:pencil-outline"></ha-icon>Renommer</button></div>
      <form id="rename-form" hidden><label for="reader-title">Nom du lecteur</label><input id="reader-title" maxlength="80" required><div class="form-actions"><button class="primary" type="submit">Enregistrer</button><button id="cancel-rename" type="button">Annuler</button></div></form>
      <div class="live-box"><div><span>PERSONNE ACTIVE</span><strong id="live-person">Aucune</strong></div><div><span>UID ACTIF</span><strong id="live-uid">Aucun</strong></div></div><p id="scan-status" class="muted" style="font-size:12px"></p>
      <div id="enroll-status" class="notice" hidden><span id="enroll-text"></span> <button id="cancel-enroll">Annuler</button></div>
      <div class="section-head" style="margin-top:24px"><div><h3>Personnes & badges</h3><p class="muted">Gère les attributions de ce lecteur.</p></div><button class="primary" id="add-person"><ha-icon icon="mdi:account-plus-outline"></ha-icon>Ajouter une personne</button></div>
      <div id="people"></div><div class="pause-settings"><label for="pause-duration">Durée lors d’une désactivation</label><select id="pause-duration"><option value="0">Jusqu’à réactivation</option><option value="900">15 minutes</option><option value="3600">1 heure</option><option value="86400">24 heures</option></select></div>
      <form id="person-form" hidden><h3 id="form-title">Nouvelle personne</h3><div class="form-grid"><div><label for="person-name">Nom de la personne</label><input id="person-name" maxlength="80" required autocomplete="off" placeholder="Ex. Camille"></div><div><label for="person-uid">UID du badge</label><input id="person-uid" maxlength="18" autocomplete="off" placeholder="A:04AABBCC ou V:…"></div></div><p class="muted" style="font-size:12px;margin-top:10px">Saisis l’UID, ou clique sur « Lire un badge » puis présente-le au lecteur sélectionné. Attente limitée à 2 minutes.</p><div class="form-actions"><button type="submit" class="primary">Enregistrer l’UID</button><button type="button" id="read-badge"><ha-icon icon="mdi:nfc"></ha-icon>Lire un badge</button><button type="button" id="use-scanned">Utiliser le badge présent</button><button type="button" id="cancel-person">Annuler</button></div></form>
      <div id="action-status" class="notice" role="status" hidden></div>
      <details id="led-details"><summary>Voyant LED · couleurs & comportements</summary><p class="muted">Personnalise ce lecteur. Le vert confirme une personne autorisée par Home Assistant ; le rose indique une personne désactivée, le rouge un badge inconnu. Tu peux éteindre chaque état.</p><p id="led-sync" class="notice" role="status"></p><form id="led-form"><div class="form-grid"><div><label for="led-brightness">Luminosité (%)</label><input id="led-brightness" type="number" min="1" max="100" required></div><div><label for="led-duration">Durée du résultat (secondes)</label><input id="led-duration" type="number" min="0.5" max="10" step="0.5" required></div></div><div id="led-states" class="led-grid"></div><div class="led-tools"><button id="led-save" class="primary" type="submit">Enregistrer les réglages LED</button><button id="led-all-off" type="button">Tout éteindre</button><button id="led-reset" type="button">Couleurs par défaut</button></div></form></details>
      <details><summary>Installation & mises à jour de ce lecteur</summary><p id="firmware-version" class="muted"></p><p><button id="converter">Installer le convertisseur Zigbee2MQTT</button></p><p id="converter-status" role="status"></p><p>Si les convertisseurs externes sont désactivés, active <b>advanced.enable_external_js</b> une fois dans Zigbee2MQTT. Pour une mise à jour sans câble, ouvre l’entité <b>Firmware du lecteur</b> sur sa fiche Home Assistant.</p><a id="device-link" href="/config/integrations/dashboard">Ouvrir la fiche du lecteur →</a></details></section>
      <div class="support"><details class="card"><summary>Installer un nouveau lecteur en USB</summary><p>ESP32-H2 DevKitM-1, 4 Mo, avec PN5180. Branche le lecteur au PC qui affiche cette page et utilise Chrome ou Edge avec Home Assistant en HTTPS.</p><p>Le premier flash installe aussi l’OTA. Un effacement complet demande un nouvel appairage Zigbee.</p><button id="prepare">Préparer le firmware USB</button><div id="install"></div><p id="status" role="status"></p></details><details class="card" style="margin-top:16px"><summary>Préparer Zigbee2MQTT avant le premier appairage</summary><p>Installe le convertisseur ZigRed sur ton Zigbee2MQTT. Si nécessaire, active advanced.enable_external_js dans ses réglages avancés et redémarre-le.</p><label for="bootstrap-base">Sujet de base Zigbee2MQTT</label><input id="bootstrap-base" value="zigbee2mqtt" autocomplete="off"><p><button id="bootstrap-converter">Installer le convertisseur</button></p><p id="bootstrap-status" role="status"></p><p>Dans Zigbee2MQTT, autorise ensuite l’appairage et allume le lecteur. Quand son identification est terminée, utilise Ajouter un lecteur en haut de cette page.</p></details></div>
      </div></div><footer class="muted">ZigRed · Chaque lecteur possède sa propre configuration. <a href="https://github.com/zaraclem/ZigRed" target="_blank" rel="noopener">Documentation</a></footer></main>`;
    this.el('refresh').onclick = () => this.loadReaders();
    this.el('add-person').onclick = () => this.editPerson();
    this.el('cancel-person').onclick = () => this.el('person-form').hidden = true;
    this.el('cancel-rename').onclick = () => this.el('rename-form').hidden = true;
    this.el('rename-reader').onclick = () => { this.el('reader-title').value=this.selected().name; this.el('rename-form').hidden=false; this.el('reader-title').focus(); };
    this.el('rename-form').onsubmit = async event => { event.preventDefault(); if(await this.action('rename_reader',{name:this.el('reader-title').value})) this.el('rename-form').hidden=true; };
    this.el('person-form').onsubmit = async event => { event.preventDefault(); if(await this.action('upsert',{name:this.el('person-name').value,uid:this.el('person-uid').value,previous_uid:this.editUid})) this.el('person-form').hidden=true; };
    this.el('read-badge').onclick = async () => { if(this.el('person-name').reportValidity() && await this.action('enroll',{name:this.el('person-name').value})) this.el('person-form').hidden=true; };
    this.el('use-scanned').onclick = () => { if(this.selected()?.scanned_uid) this.el('person-uid').value=this.selected().scanned_uid; else this.notice('action-status','Présente un badge au lecteur sélectionné.',true); };
    this.el('cancel-enroll').onclick = () => this.action('cancel');
    this.el('converter').onclick = () => this.installConverter();
    this.el('prepare').onclick = () => this.prepare();
    this.el('bootstrap-converter').onclick = () => this.installBootstrapConverter();
    this.ledStates=[['idle','En attente','#087ead',false],['authorized','Personne autorisée','#00ff00',false],['denied','Personne désactivée','#ff1493',false],['unknown','Badge inconnu','#ff0000',false],['pending','Vérification dans HA','#ffb000',true],['pairing','Connexion Zigbee','#ffb000',true],['error','Erreur du lecteur','#ff0000',true],['ota','Mise à jour','#aa00ff',true]];
    for(const [key,label] of this.ledStates){
      const row=document.createElement('div');row.className='led-row';
      row.innerHTML=`<label><input id="led-${key}-enabled" type="checkbox">${label}</label><input id="led-${key}-color" type="color" aria-label="Couleur : ${label}"><select id="led-${key}-blink" aria-label="Comportement : ${label}"><option value="steady">Fixe</option><option value="blink">Clignotant</option></select>`;
      this.el('led-states').append(row);
    }
    this.el('led-form').oninput=()=>{this.ledDirty=true;};
    this.el('led-form').onsubmit=async event=>{
      event.preventDefault();const settings={brightness:Number(this.el('led-brightness').value),duration:Math.round(Number(this.el('led-duration').value)*1000),states:{}};
      for(const [key] of this.ledStates)settings.states[key]={enabled:this.el(`led-${key}-enabled`).checked,color:this.el(`led-${key}-color`).value,blink:this.el(`led-${key}-blink`).value==='blink'};
      this.el('led-save').disabled=true;
      try{if(await this.action('led',{settings})){this.ledDirty=false;this.ledSignature=null;this.render();}}
      finally{this.el('led-save').disabled=false;}
    };
    this.el('led-all-off').onclick=()=>{for(const [key] of this.ledStates)this.el(`led-${key}-enabled`).checked=false;this.ledDirty=true;};
    this.el('led-reset').onclick=()=>{this.fillLED({brightness:15,duration:2000,states:Object.fromEntries(this.ledStates.map(([key,,color,blink])=>[key,{enabled:true,color,blink}]))});this.ledDirty=true;};
  }
  fillLED(settings){
    this.el('led-brightness').value=settings.brightness;this.el('led-duration').value=settings.duration/1000;
    for(const [key] of this.ledStates){const state=settings.states[key];this.el(`led-${key}-enabled`).checked=state.enabled;this.el(`led-${key}-color`).value=state.color;this.el(`led-${key}-blink`).value=state.blink?'blink':'steady';}
  }
  renderLED(reader){
    if(!reader.led){this.el('led-details').hidden=true;return;}this.el('led-details').hidden=false;
    if(this.ledReader!==reader.entry_id){this.ledReader=reader.entry_id;this.ledDirty=false;this.ledSignature=null;}
    const signature=JSON.stringify(reader.led);
    if(!this.ledDirty&&signature!==this.ledSignature){this.fillLED(reader.led);this.ledSignature=signature;}
    this.el('led-sync').textContent=reader.led_error?`Enregistré dans HA · envoi à réessayer : ${reader.led_error}`:!reader.led_capable?'Installe le firmware 0.5.0 ou supérieur et le nouveau convertisseur pour appliquer ces réglages.':reader.led_synced?'Réglages confirmés par le lecteur.':'Réglages enregistrés dans HA · attente de confirmation du lecteur.';
    this.el('led-save').disabled=this.busy||!reader.paired;
  }
  el(id) { return this.shadowRoot.getElementById(id); }
  progress(id, message, percent=null, state='working') {
    const node=this.el(id); node.replaceChildren(); node.className=`notice install-progress ${state}`;
    node.setAttribute('aria-busy',String(state==='working'));
    const label=document.createElement('div'); label.textContent=message; node.append(label);
    if(state==='working' || state==='success') {
      const bar=document.createElement('progress'); bar.max=100;
      bar.setAttribute('aria-label',message);
      if(percent!==null) bar.value=Math.max(0,Math.min(100,percent));
      node.append(bar);
    }
  }
  async converterRequest(statusId, payload) {
    const started=Date.now();
    const update=()=>this.progress(statusId,`Installation en cours · attente de confirmation Zigbee2MQTT (${Math.floor((Date.now()-started)/1000)} s, délai maximal 30 s)…`);
    update(); const timer=setInterval(update,1000);
    try { const result=await this._hass.callApi('POST','zigred/converter',payload); clearInterval(timer); this.progress(statusId,result.message,100,'success'); }
    catch(error) { clearInterval(timer); this.progress(statusId,error.message || 'Installation impossible. Vérifie MQTT et Zigbee2MQTT.',null,'error'); }
    finally { clearInterval(timer); }
  }
  selected() { return this.readers.find(reader => reader.entry_id === this.selectedId); }
  notice(id,message,error=false) { const node=this.el(id); node.textContent=message; node.hidden=!message; node.classList.toggle('error',error); }
  async loadReaders() {
    if (!this._hass || this.loadingReaders || this.busy || !this.isConnected) return;
    this.loadingReaders=true; const requestVersion=this.actionVersion || 0;
    try {
      const data=await this._hass.callApi('GET','zigred/readers');
      if (!this.isConnected || this.busy || requestVersion !== (this.actionVersion || 0)) return;
      this.readers=data.readers; this.readersLoaded=true;
      if (!this.selected()) { this.selectedId=this.readers[0]?.entry_id || null; this.el('person-form').hidden=true; this.el('rename-form').hidden=true; }
      this.notice('page-status',''); this.render();
    } catch(error) { this.notice('page-status',error.message || 'Impossible de charger les lecteurs. Vérifie ta connexion à Home Assistant.',true); }
    finally { this.loadingReaders=false; }
  }
  render() {
    this.el('count-readers').textContent=this.readers.length;
    this.el('count-people').textContent=this.readers.reduce((sum,r)=>sum+r.people.length,0);
    this.el('count-live').textContent=this.readers.filter(r=>r.present).length;
    const signature=JSON.stringify(this.readers.map(r=>[r.entry_id,r.name,r.topic,r.present,r.people.length,r.paired,r.ieee_address,r.converter_ready]))+this.selectedId;
    if (signature!==this.readerSignature) {
      this.readerSignature=signature; this.el('readers').replaceChildren();
      for(const reader of this.readers) {
        const button=document.createElement('button'); button.className='reader'+(reader.entry_id===this.selectedId?' selected':''); button.setAttribute('aria-pressed',String(reader.entry_id===this.selectedId));
        const name=document.createElement('strong'); name.textContent=reader.name;
        const topic=document.createElement('small'); topic.textContent=reader.topic;
        const badge=document.createElement('span'); badge.className='pill'+(reader.present?' live':''); badge.textContent=!reader.paired?'À associer':reader.present?'● Lecture en cours':`${reader.people.length} personne(s)`;
        button.append(name,topic,badge); button.disabled=!!this.installingConverter; button.onclick=()=>{if(this.installingConverter)return;this.selectedId=reader.entry_id;this.peopleSignature=null;this.el('person-form').hidden=true;this.el('rename-form').hidden=true;this.notice('action-status','');this.el('converter-status').textContent='';this.render();}; this.el('readers').append(button);
      }
    }
    const reader=this.selected(); this.el('detail').hidden=!reader; this.el('welcome').hidden=!!reader;
    if(!reader) return;
    this.el('reader-name').textContent=reader.name; this.el('reader-topic').textContent=`${reader.topic} · ${reader.ieee_address || 'Adresse Zigbee non vérifiée'}`;
    this.el('live-person').textContent=reader.current_person || 'Aucune'; this.el('live-uid').textContent=reader.current_uid || 'Aucun';
    const scanned=reader.people.find(p=>p.uid===reader.scanned_uid);
    this.el('scan-status').textContent=!reader.paired ? 'Ce lecteur n’a pas été retrouvé dans Zigbee2MQTT. Appaire-le puis utilise Reconfigurer sur la fiche de l’intégration pour l’associer.' : !reader.converter_ready ? 'Lecteur appairé et identifié. Installe le convertisseur Zigbee2MQTT ci-dessous pour recevoir ses lectures.' : scanned && !scanned.enabled ? `Badge de ${scanned.name} détecté · personne désactivée, ignorée par les entités.` : reader.present ? '● Lecture en cours sur ce lecteur' : 'En attente d’un badge · aucune lecture en cours';
    this.el('enroll-status').hidden=!reader.enrolling; this.el('enroll-text').textContent=`Présente un nouveau badge à ${reader.name} pour ${reader.pending_name}. Retire d’abord tout badge déjà présent.`;
    this.el('add-person').disabled=!reader.paired;
    this.el('firmware-version').textContent=`Firmware : ${reader.firmware_version || 'en attente du lecteur'}`;
    this.el('device-link').href=`/config/integrations/integration/zigred#${encodeURIComponent(reader.entry_id)}`;
    this.renderLED(reader);
    const peopleSignature=reader.entry_id+JSON.stringify(reader.people);
    if(peopleSignature===this.peopleSignature) return; this.peopleSignature=peopleSignature;
    const list=this.el('people'); list.replaceChildren();
    if(!reader.people.length) { const empty=document.createElement('div'); empty.className='empty'; empty.textContent='Aucune personne sur ce lecteur. Ajoute la première avec son badge.'; list.append(empty); }
    for(const person of reader.people) {
      const row=document.createElement('div'); row.className='person';
      const identity=document.createElement('div'); identity.className='identity'; const name=document.createElement('strong'); name.textContent=person.name;
      const uid=document.createElement('small'); uid.textContent=person.uid; const state=document.createElement('small');
      state.textContent=!person.enabled ? (person.disabled_until ? `Désactivée jusqu’au ${new Date(person.disabled_until*1000).toLocaleString()}` : 'Désactivée · réactivation manuelle') : person.present ? '● Lecture en cours' : 'Autorisée';
      identity.append(name,uid,state); const actions=document.createElement('div'); actions.className='actions';
      const edit=document.createElement('button'); edit.textContent='Modifier'; edit.onclick=()=>this.editPerson(person);
      const toggle=document.createElement('button'); toggle.textContent=person.enabled?'Désactiver':'Réactiver'; toggle.onclick=()=>this.action('toggle',{uid:person.uid,enabled:!person.enabled,seconds:Number(this.el('pause-duration').value)});
      const remove=document.createElement('button'); remove.className='danger'; remove.textContent='Supprimer'; remove.onclick=()=>{if(confirm(`Supprimer ${person.name} (${person.uid}) uniquement du lecteur ${reader.name} ?`)) this.action('remove',{uid:person.uid});};
      actions.append(edit,toggle,remove); row.append(identity,actions); list.append(row);
    }
    this.shadowRoot.querySelectorAll('#people button').forEach(button=>button.disabled=!!this.busy || !reader.paired);
  }
  editPerson(person=null) {
    this.editUid=person?.uid || null; this.el('person-form').hidden=false; this.el('form-title').textContent=person?'Modifier la personne':'Nouvelle personne';
    this.el('person-name').value=person?.name || ''; this.el('person-uid').value=person?.uid || ''; this.el('person-uid').readOnly=false;
    this.el('read-badge').hidden=!!person; this.el('use-scanned').hidden=!!person; this.el('person-name').focus();
  }
  async action(action,data={}) {
    if(this.busy || !this.selectedId) return false;
    this.busy=true; this.actionVersion=(this.actionVersion || 0)+1; const entryId=this.selectedId;
    const buttons=[...this.shadowRoot.querySelectorAll('#detail button')]; buttons.forEach(button=>button.disabled=true);
    this.notice('action-status','Enregistrement…');
    try {
      const updated=await this._hass.callApi('POST','zigred/readers',{entry_id:entryId,action,...data});
      const index=this.readers.findIndex(reader=>reader.entry_id===entryId); if(index>=0) this.readers[index]=updated;
      this.notice('action-status','Modification enregistrée sur ce lecteur.'); this.peopleSignature=null; this.render(); return true;
    } catch(error) { this.notice('action-status',error.message || 'Impossible d’enregistrer cette modification.',true); return false; }
    finally { this.busy=false; buttons.forEach(button=>button.disabled=false); this.peopleSignature=null; this.render(); }
  }
  async installConverter() {
    const button=this.el('converter'), status=this.el('converter-status'), entryId=this.selectedId;
    if(!entryId || this.installingConverter) return;
    this.installingConverter=true; button.disabled=true;
    this.shadowRoot.querySelectorAll('.reader').forEach(node=>node.disabled=true);
    try { await this.converterRequest('converter-status',{entry_id:entryId}); }
    finally { this.installingConverter=false; button.disabled=false; this.shadowRoot.querySelectorAll('.reader').forEach(node=>node.disabled=false); }
  }
  async installBootstrapConverter() {
    const button=this.el('bootstrap-converter'), status=this.el('bootstrap-status');
    if(button.disabled) return; button.disabled=true; this.el('bootstrap-base').disabled=true;
    try {
      await this.converterRequest('bootstrap-status',{base_topic:this.el('bootstrap-base').value.trim().replace(/\/+$/,'')});
    } finally { button.disabled=false; this.el('bootstrap-base').disabled=false; }
  }
  async prepare() {
    if(this.usbBusy) return;
    const root = this.shadowRoot, button = root.getElementById('prepare'), status = root.getElementById('status');
    button.disabled = true;
    root.getElementById('install').replaceChildren();
    for (const url of this.urls || []) URL.revokeObjectURL(url);
    this.urls = [];
    try {
      if (!window.isSecureContext || !navigator.serial) throw new Error('Utilise Chrome ou Edge avec Home Assistant en HTTPS (ou localhost).');
      this.progress('status','Recherche de la dernière version…');
      const metadata = await this._hass.callApi('GET', 'zigred/firmware');
      this.progress('status','Téléchargement depuis GitHub et vérification du firmware par Home Assistant…');
      const response = await this._hass.fetchWithAuth('/api/zigred/firmware/usb');
      if (response.status === 401) throw new Error('Session Home Assistant expirée. Reconnecte-toi puis réessaie.');
      if (response.status === 403) throw new Error('Un compte administrateur Home Assistant est nécessaire pour préparer le firmware.');
      if (!response.ok) throw new Error('Firmware indisponible ou invalide. Consulter GitHub Actions.');
      const firmware = URL.createObjectURL(await response.blob()); this.urls.push(firmware);
      const manifest = URL.createObjectURL(new Blob([JSON.stringify({name:'ZigRed', version:metadata.version,
        new_install_prompt_erase:true, builds:[{chipFamily:'ESP32-H2', parts:[{path:firmware,offset:0}]}]})], {type:'application/json'}));
      this.urls.push(manifest);
      this.progress('status','Chargement de l’outil de flash USB…');
      const {flash}=await import('https://esm.sh/esp-web-tools@10.1.1/dist/flash.js?bundle');
      const trigger = document.createElement('button'); trigger.className='primary'; trigger.textContent=`Installer ZigRed ${metadata.version}`;
      const eraseLabel=document.createElement('label'), erase=document.createElement('input'); erase.type='checkbox'; erase.style.cssText='display:inline;width:auto;min-height:0;margin-right:8px';
      eraseLabel.append(erase,'Effacement complet (supprime l’appairage Zigbee)');
      trigger.onclick=()=>this.flashUSB(flash,manifest,{name:'ZigRed',version:metadata.version,builds:[{chipFamily:'ESP32-H2',parts:[{path:firmware,offset:0}]}]},erase.checked,trigger,erase);
      root.getElementById('install').replaceChildren(eraseLabel,trigger);
      this.progress('status','Firmware vérifié. Clique sur Installer, puis sélectionne le port USB du lecteur.',null,'ready');
    } catch (error) { this.progress('status',error.message || 'Aucune version publiée. Consulter GitHub Actions.',null,'error'); }
    finally { button.disabled=false; }
  }
  async flashUSB(flash,manifestPath,manifest,eraseFirst,button,erase) {
    if(this.usbBusy) return;
    this.usbBusy=true; button.disabled=true; erase.disabled=true; this.el('prepare').disabled=true;
    let port,finished=false,failed=false;
    this.progress('status','Sélectionne le port USB dans la fenêtre du navigateur…',null,'ready');
    try {
      port=await navigator.serial.requestPort();
      this.progress('status','Connexion au lecteur · maintiens BOOT si la connexion ne démarre pas…');
      await flash(update=>{
        const labels={initializing:'Connexion au lecteur…',preparing:'Préparation de l’écriture…',erasing:'Effacement de la mémoire…',writing:'Écriture du firmware',finished:'Installation terminée · lecteur redémarré. Tu peux maintenant l’appairer dans Zigbee2MQTT.'};
        if(update.state==='error') {
          failed=true;
          const errors={failed_initialize:'Connexion impossible. Réessaie en maintenant BOOT sur le lecteur.',not_supported:'Carte incompatible : un ESP32-H2 est nécessaire.',failed_firmware_download:'Firmware inaccessible. Prépare-le à nouveau.',write_failed:'Écriture interrompue. Vérifie le câble USB puis réessaie.'};
          this.progress('status',errors[update.details?.error] || update.message || 'Le flash a échoué.',null,'error'); return;
        }
        if(update.state==='finished') { finished=true; this.progress('status',labels.finished,100,'success'); return; }
        const percent=update.state==='writing' && Number.isFinite(update.details?.percentage)?update.details.percentage:null;
        this.progress('status',(labels[update.state] || 'Installation en cours…')+(percent!==null?` · ${percent} %`:''),percent);
      },port,manifestPath,manifest,eraseFirst);
      if(!finished && !failed) this.progress('status','Installation interrompue. Réessaie.',null,'error');
    } catch(error) {
      if(!failed && !finished) this.progress('status',error.name==='NotFoundError'?'Sélection du port annulée. Clique sur Installer pour réessayer.':error.message || 'Connexion USB impossible.',null,error.name==='NotFoundError'?'ready':'error');
    } finally {
      try { if(port?.readable || port?.writable) await port.close(); } catch(_) {}
      this.usbBusy=false; button.disabled=false; erase.disabled=false; this.el('prepare').disabled=false;
      if(!this.isConnected) { for(const url of this.urls || []) URL.revokeObjectURL(url); this.urls=[]; }
    }
  }
  disconnectedCallback() {
    clearInterval(this.poll);
    if(this.usbBusy) return;
    for (const url of this.urls || []) URL.revokeObjectURL(url);
    this.urls=[]; this.el('install')?.replaceChildren();
  }
}
if (!customElements.get('zigred-panel')) customElements.define('zigred-panel',ZigRedPanel);
