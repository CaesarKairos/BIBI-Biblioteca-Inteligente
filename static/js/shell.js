iniciarRedimensionamentoPaineis();
document.querySelectorAll('.nav-menu li[id]').forEach(item=>{
 const active=item.id==='m-'+document.body.dataset.page;item.classList.toggle('active',active);
 const link=document.createElement('a');link.href='/app#'+item.id.slice(2);
 if(active)link.setAttribute('aria-current','page');
 while(item.firstChild)link.append(item.firstChild);item.append(link);
});
document.querySelector('.logo')?.addEventListener('click',()=>location.assign('/app'));
document.getElementById('theme-toggle-btn')?.addEventListener('click',()=>{
 const dark=document.body.classList.toggle('dark-mode');
 const config=JSON.parse(localStorage.getItem('bibiConfig')||'{}');config.darkMode=dark;localStorage.setItem('bibiConfig',JSON.stringify(config));
 accountApi('/api/minha-conta/preferencias','PUT',{tema:dark?'escuro':'claro'}).catch(()=>{});
});
const motion=matchMedia('(prefers-reduced-motion: reduce)');
const mascot=document.querySelector('.cat-waving');
function updateMotion(){if(motion.matches)mascot?.pause();else mascot?.play().catch(()=>{});}
motion.addEventListener('change',updateMotion);updateMotion();

document.querySelectorAll('.logo,.theme-item').forEach(control=>{control.tabIndex=0;control.setAttribute('role','button');control.setAttribute('aria-label',control.title||'Abrir acervo');control.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();control.click();}});});
