try { document.body.classList.toggle('dark-mode',JSON.parse(localStorage.getItem('bibiConfig')||'{}').darkMode===true); } catch {}
