/* Local photo preparation. Device originals are never modified or uploaded. */
(function (root) {
  'use strict';
  const MAX_FILE_BYTES = 50 * 1024 * 1024;
  const MAX_OUTPUT_BYTES = 2 * 1024 * 1024;
  const MAX_EDGE = 3072;
  const MAX_PIXELS = 100 * 1000 * 1000;
  const formats = /^(?:image\/(?:jpeg|jpg|png|webp|avif|gif|heic|heif|heic-sequence|heif-sequence))$/i;
  const extensions = /\.(?:jpe?g|png|webp|avif|gif|heic|heif)$/i;

  function decodeWithImage(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file), image = new Image();
      let settled = false;
      const finish = error => {
        if (settled) return;
        settled = true; clearTimeout(timer); image.onload = image.onerror = null;
        URL.revokeObjectURL(url);
        if (error) { image.src = ''; reject(error); }
        else resolve({ source: image, width: image.naturalWidth, height: image.naturalHeight, close: () => { image.src = ''; } });
      };
      const timer = setTimeout(() => finish(new Error('사진을 읽는 시간이 초과됐습니다. JPG로 저장한 사진을 다시 올려주세요.')), 30000);
      image.onload = () => finish();
      image.onerror = () => finish(new Error('image_decode_failed'));
      image.src = url;
    });
  }

  async function decode(file) {
    if (typeof root.createImageBitmap === 'function') {
      try {
        const bitmap = await root.createImageBitmap(file, { imageOrientation: 'from-image' });
        return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close() };
      } catch { /* Older Safari and some native photo decoders need an Image. */ }
    }
    return decodeWithImage(file);
  }

  function jpegBlob(canvas, quality) {
    return new Promise((resolve, reject) => canvas.toBlob(blob => {
      if (blob && blob.size && blob.type === 'image/jpeg') resolve(blob);
      else reject(new Error('사진을 준비하지 못했습니다. 열어둔 탭을 줄이거나 다른 사진을 선택해주세요.'));
    }, 'image/jpeg', quality));
  }

  function dataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => typeof reader.result === 'string' && reader.result.startsWith('data:image/jpeg;base64,')
        ? resolve(reader.result) : reject(new Error('사진 사본을 읽지 못했습니다. 다시 선택해주세요.'));
      reader.onerror = () => reject(new Error('사진 사본을 읽지 못했습니다. 다시 선택해주세요.'));
      reader.readAsDataURL(blob);
    });
  }

  async function read(file) {
    if (!file || typeof file.size !== 'number' || typeof file.slice !== 'function' || !file.size) {
      throw new Error('비어 있거나 올바르지 않은 사진 파일입니다. 다른 사진을 선택해주세요.');
    }
    if (file.size > MAX_FILE_BYTES) throw new Error('사진은 한 장당 50MB까지 올릴 수 있습니다. 기기에서 더 작은 사본으로 저장해주세요.');
    const type = String(file.type || '').toLowerCase();
    if (!formats.test(type) && !((!type || type === 'application/octet-stream') && extensions.test(String(file.name || '')))) {
      throw new Error('JPG, PNG, WebP, AVIF, GIF 사진을 사용해주세요. HEIC·HEIF는 브라우저에서 읽을 수 있을 때 지원합니다.');
    }
    let decoded;
    try { decoded = await decode(file); }
    catch {
      if (/hei[cf]/i.test(type + String(file.name || ''))) throw new Error('현재 브라우저가 이 HEIC·HEIF 사진을 읽지 못합니다. 기기에서 JPG로 저장한 뒤 올려주세요.');
      throw new Error('손상되었거나 브라우저에서 읽을 수 없는 사진입니다. JPG 또는 PNG로 저장한 뒤 다시 올려주세요.');
    }
    const canvas = document.createElement('canvas');
    try {
      if (!decoded.width || !decoded.height || decoded.width * decoded.height > MAX_PIXELS) {
        throw new Error('사진 해상도가 너무 큽니다. 1억 화소 이하의 사본을 선택해주세요.');
      }
      let edge = Math.min(MAX_EDGE, Math.max(decoded.width, decoded.height));
      for (let attempt = 0; attempt < 8; attempt++) {
        const scale = Math.min(1, edge / Math.max(decoded.width, decoded.height));
        canvas.width = Math.max(1, Math.round(decoded.width * scale));
        canvas.height = Math.max(1, Math.round(decoded.height * scale));
        const context = canvas.getContext('2d');
        if (!context) throw new Error('사진을 준비할 메모리가 부족합니다. 다른 탭을 닫고 다시 시도해주세요.');
        context.fillStyle = '#ffffff'; context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(decoded.source, 0, 0, canvas.width, canvas.height);
        for (const quality of [.94, .88, .82]) {
          const blob = await jpegBlob(canvas, quality);
          if (blob.size <= MAX_OUTPUT_BYTES) return await dataUrl(blob);
        }
        edge = Math.max(256, Math.floor(edge * .8));
      }
      throw new Error('사진 용량을 안전하게 줄이지 못했습니다. 더 작은 JPG 사본을 선택해주세요.');
    } finally {
      decoded.close(); canvas.width = canvas.height = 1;
    }
  }

  root.MuseImages = Object.freeze({ read, MAX_FILE_BYTES, MAX_OUTPUT_BYTES, MAX_EDGE, MAX_PIXELS });
})(typeof globalThis === 'object' ? globalThis : this);
