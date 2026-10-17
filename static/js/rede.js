(() => {
    const address=document.getElementById('network-address');
    const status=document.getElementById('network-status');
    const copy=document.getElementById('copy-network');
    const diagnostic=document.getElementById('network-diagnostic');
    async function refresh(){
        const state=await accountApi('/api/gestao/rede');
        status.textContent=state.erro || (state.ativo?'Servidor HTTPS em execução. '+(state.bandeja?'Pode permanecer na bandeja do Windows.':'Mantenha o aplicativo aberto, mesmo minimizado.'):'Servidor de rede indisponível.');
        address.value=state.enderecos[0]?.url || '';
        address.placeholder='Conecte este computador a uma rede local.';
        copy.disabled=!state.ativo||!address.value;
        const list=document.getElementById('network-addresses');list.replaceChildren();
        for(const item of state.enderecos){
            const row=accountText('p',`${item.interface}: ${item.url}`);list.append(row);
        }
        document.getElementById('network-fingerprint').textContent=state.certificado_sha256 || 'Certificado ainda não disponível.';
        document.getElementById('network-certificate').hidden=!state.certificado_sha256;
        if(!state.enderecos.length&&!state.erro)status.textContent+=' Nenhum endereço IPv4 de rede privada foi encontrado. Confira a conexão Wi-Fi ou Ethernet.';
    }
    accountAction(copy,async()=>{
        try{await navigator.clipboard.writeText(address.value);diagnostic.textContent='Endereço copiado.';}
        catch{address.focus();address.select();diagnostic.textContent='Endereço selecionado. Use Ctrl+C para copiar.';}
    });
    accountAction(document.getElementById('refresh-network'),refresh);
    accountAction(document.getElementById('diagnose-network'),async()=>{
        diagnostic.textContent='Verificando a conexão TLS…';
        const result=await accountApi('/api/gestao/rede/diagnostico','POST',{});
        diagnostic.textContent=result.resultados.map(item=>`${item.interface}: ${item.conectou?'conexão segura estabelecida':'falha na conexão'}`).join(' · ')+'. '+result.aviso;
    });
    window.settingsNetworkReady=refresh();
})();
