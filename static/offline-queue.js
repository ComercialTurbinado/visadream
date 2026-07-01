/**
 * Fila offline de leads — IndexedDB + sincronização quando a internet voltar.
 */
const VisaDreamOffline = (() => {
  const DB_NAME = 'visadream_offline';
  const STORE = 'pending_leads';
  const DB_VERSION = 1;

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve(req.result);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          const store = db.createObjectStore(STORE, { keyPath: 'id' });
          store.createIndex('createdAt', 'createdAt', { unique: false });
        }
      };
    });
  }

  async function add(item) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.oncomplete = () => resolve(item.id);
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE).put(item);
    });
  }

  async function list() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => {
        const rows = (req.result || []).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
        resolve(rows);
      };
      req.onerror = () => reject(req.error);
    });
  }

  async function remove(id) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE).delete(id);
    });
  }

  async function update(item) {
    return add(item);
  }

  async function count() {
    const rows = await list();
    return rows.length;
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = () => reject(r.error);
      r.readAsDataURL(file);
    });
  }

  function base64ToFile(dataUrl, name, type) {
    const [meta, b64] = dataUrl.split(',');
    const mime = type || (meta.match(/data:([^;]+)/) || [])[1] || 'image/jpeg';
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new File([arr], name || 'photo.jpg', { type: mime });
  }

  async function enqueue({ payload, photoFile }) {
    const id = crypto.randomUUID();
    const item = {
      id,
      createdAt: new Date().toISOString(),
      payload,
      photoName: '',
      photoType: '',
      photoData: '',
      attempts: 0,
      lastError: '',
    };
    if (photoFile) {
      item.photoName = photoFile.name || 'photo.jpg';
      item.photoType = photoFile.type || 'image/jpeg';
      item.photoData = await fileToBase64(photoFile);
    }
    await add(item);
    return id;
  }

  async function buildFormData(item, turnstileToken, offlineMarker) {
    const fd = new FormData();
    fd.append('payload', JSON.stringify(item.payload));
    if (item.photoData) {
      const file = base64ToFile(item.photoData, item.photoName, item.photoType);
      fd.append('photo', file);
    }
    const token = turnstileToken || (offlineMarker && !turnstileToken ? offlineMarker : '');
    if (token) fd.append('cf_turnstile_response', token);
    return fd;
  }

  return {
    enqueue,
    list,
    remove,
    update,
    count,
    buildFormData,
  };
})();
