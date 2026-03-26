document.addEventListener('DOMContentLoaded', () => {
    // Dropzones
    setupDropZone('drop-excel-militar', 'file-excel-militar', 'excel_militar', 'status-excel-militar');
    setupDropZone('drop-excel-admin', 'file-excel-admin', 'excel_administrativo', 'status-excel-admin');
    setupDropZone('drop-fotos', 'file-fotos', 'fotos', 'status-fotos');
    setupDropZone('drop-plantillas', 'file-plantillas', 'plantillas', null, true);
    setupDropZone('drop-insignias', 'file-insignias', 'insignias', null, true, loadInsignias);

    loadInsignias();
    
    // Toggle Logic
    const radios = document.querySelectorAll('input[name="tipo_personal"]');
    radios.forEach(r => r.addEventListener('change', handleToggleStatus));
    
    // Initial sync
    handleToggleStatus();

    // Generate action
    document.getElementById('btn-generar').addEventListener('click', generateCarnets);
});

function handleToggleStatus() {
    const isMilitar = document.getElementById('btn-militar').checked;
    
    const alertMilitar = document.getElementById('alert-militar');
    const alertAdmin = document.getElementById('alert-admin');
    
    const boxInsignias = document.getElementById('box-insignias');
    const insigniasContainer = document.getElementById('insignias-container');
    const plantillaHelper = document.getElementById('plantilla-helper');

    if (isMilitar) {
        alertMilitar.classList.remove('hidden');
        alertMilitar.classList.add('active');
        alertAdmin.classList.add('hidden');
        alertAdmin.classList.remove('active');
        
        // Toggle excel boxes
        document.getElementById('section-excel-militar').style.display = 'block';
        document.getElementById('section-excel-admin').style.display = 'none';
        
        // Show military specific boxes
        boxInsignias.style.display = 'block';
        insigniasContainer.style.display = 'block';
        plantillaHelper.innerText = "TIF Alta Resolución (Solo requiere Frontal)";
        
    } else {
        alertAdmin.classList.remove('hidden');
        alertAdmin.classList.add('active');
        alertMilitar.classList.add('hidden');
        alertMilitar.classList.remove('active');
        
        // Toggle excel boxes
        document.getElementById('section-excel-militar').style.display = 'none';
        document.getElementById('section-excel-admin').style.display = 'block';
        
        // Hide military specific boxes
        boxInsignias.style.display = 'none';
        insigniasContainer.style.display = 'none';
        plantillaHelper.innerText = "Sube Frontal (template_final.tif) y Trasero (template_reverso.tif)";
    }
}

function setupDropZone(zoneId, inputId, tipo, statusId, suppressStatus=false, callback=null) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    if(!zone || !input) return;

    zone.addEventListener('dragover', e => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', e => {
        e.preventDefault();
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            input.files = e.dataTransfer.files;
            uploadFiles(input.files, tipo, statusId, suppressStatus, callback);
        }
    });

    input.addEventListener('change', () => {
        if (input.files.length) {
            uploadFiles(input.files, tipo, statusId, suppressStatus, callback);
        }
    });
}

function getBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = error => reject(error);
    });
}

async function uploadFiles(files, tipo, statusId, suppressStatus, callback) {
    let uploadedCount = 0;
    const statusEl = statusId ? document.getElementById(statusId) : null;
    
    if (statusEl && !suppressStatus) {
        statusEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Subiendo ${files.length} archivo(s)...`;
    }

    for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);

        try {
            const res = await fetch(`/upload/${tipo}`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) uploadedCount++;
        } catch (err) {
            console.error(err);
        }
    }

    if (statusEl && !suppressStatus) {
        statusEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${uploadedCount} archivo(s) procesados y almacenados con éxito.`;
    }

    if (callback) callback();
}

async function loadInsignias() {
    try {
        const res = await fetch('/insignias');
        const data = await res.json();
        const ul = document.getElementById('insignias-ul');
        if(!ul) return;
        ul.innerHTML = '';

        if(data.insignias.length === 0){
            ul.innerHTML = '<li style="border:none;background:rgba(255,255,255,0.2);color:#666;">No hay insignias guardadas en el servidor.</li>';
        }

        data.insignias.forEach(ins => {
            const li = document.createElement('li');
            li.innerHTML = `${ins} <button class="btn-delete" onclick="deleteInsignia('${ins}')"><i class="fa-solid fa-xmark"></i></button>`;
            ul.appendChild(li);
        });
    } catch(e) {}
}

async function deleteInsignia(name) {
    if(confirm(`¿Seguro que deseas eliminar la insignia '${name}'?`)) {
        await fetch(`/delete_insignia/${name}`, { method: 'DELETE' });
        loadInsignias();
    }
}

async function generateCarnets() {
    const btn = document.getElementById('btn-generar');
    const spinner = document.getElementById('loading-spinner');
    const dlLink = document.getElementById('download-link');

    // Get selected type
    const tipoPersonal = document.querySelector('input[name="tipo_personal"]:checked').value;

    btn.classList.add('hidden');
    spinner.classList.remove('hidden');
    dlLink.classList.add('hidden');

    try {
        // Enviar JSON con el tipo
        const res = await fetch('/generate', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ tipo_personal: tipoPersonal })
        });
        const data = await res.json();

        if (data.status === 'success') {
            spinner.classList.add('hidden');
            dlLink.innerHTML = `<a href="${data.url}" download><i class="fa-solid fa-file-zipper"></i> Descargar Zip Final (${data.filename})</a>`;
            dlLink.classList.remove('hidden');
            btn.classList.remove('hidden');
            btn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Generar Nuevamente`;
        } else {
            alert('❌ Atención:\n\n' + (data.error || 'Error Desconocido'));
            btn.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    } catch (e) {
        alert('❌ Error crítico en el servidor al intentar generar archivos.');
        btn.classList.remove('hidden');
        spinner.classList.add('hidden');
    }
}
