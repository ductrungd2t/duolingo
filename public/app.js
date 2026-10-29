import {Runner} from './runner.js';
const $ = id => document.getElementById(id);
let token = '', loading = false, apiBase = '';
try { apiBase = localStorage.getItem('duo-api-base') || ''; } catch {}
$('api-base').value = apiBase;
const dialog = $('settings');
function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
function log(message) {
  $('logs').querySelector('.empty')?.remove();
  const item = document.createElement('li'), time = document.createElement('time'), text = document.createElement('span');
  time.textContent = new Date().toLocaleTimeString('vi-VN', {timeZone:'Asia/Ho_Chi_Minh'});
  text.textContent = message; item.append(time, text); $('logs').prepend(item);
  while ($('logs').children.length > 200) $('logs').lastElementChild.remove();
}
async function request(path) {
  if (!token) throw new Error('Mở Cài đặt và nhập token tài khoản trung.');
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(`${apiBase}${path}`, {method:'POST', headers:{Authorization:`Bearer ${token}`}, signal:controller.signal, cache:'no-store', credentials:'omit', redirect:'error'});
    const type = response.headers.get('content-type') || '';
    if (!type.includes('application/json')) throw new Error('Chưa kết nối được API Python. Nếu dùng GitHub Pages, nhập URL Render trong Cài đặt.');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Máy chủ báo lỗi ${response.status}.`);
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Quá thời gian chờ. Kết quả yêu cầu chưa xác định; không tự gửi lại.');
    if (error instanceof TypeError) throw new Error('Không kết nối được API. Kiểm tra URL máy chủ, mạng và cấu hình ALLOWED_ORIGINS.');
    throw error;
  } finally { clearTimeout(timer); }
}
function render(state) {
  $('run-status').textContent = state.status || 'Sẵn sàng bắt đầu';
  $('run-count').textContent = `${state.accepted || 0} / ${state.total || $('count').value}`;
  $('progress').max = state.total || Number($('count').value) || 10;
  $('progress').value = state.accepted || 0;
  $('state-pill').textContent = state.stopping && state.running ? 'Đang dừng' : state.running ? state.paused ? 'Tạm dừng' : 'Đang chạy' : 'Sẵn sàng';
  $('start').disabled = state.running || !token;
  $('pause').disabled = !state.running || state.stopping;
  $('stop').disabled = !state.running || state.stopping;
  $('pause').textContent = state.paused ? 'Tiếp tục' : 'Tạm dừng';
  $('count').disabled = $('interval').disabled = state.running;
  $('settings-open').disabled = state.running || loading;
  $('refresh').disabled = loading || !token;
}
const runner = new Runner({send:() => request('/api/complete'), onChange:render, onLog:log});
$('start').addEventListener('click', () => {
  const count = Number($('count').value), interval = Number($('interval').value);
  if (!Number.isInteger(count) || count < 1 || count > 10000 || !Number.isFinite(interval) || interval < 1 || interval > 3600) {
    notice('Số lượt từ 1–10000; khoảng nghỉ từ 1–3600 giây.'); return;
  }
  notice(''); log(`Bắt đầu ${count} lượt, khoảng nghỉ ${interval} giây.`);
  runner.start(count, interval);
});
$('pause').addEventListener('click', () => runner.pause());
$('stop').addEventListener('click', () => runner.stop());
$('refresh').addEventListener('click', async () => {
  if (loading) return;
  loading = true; $('refresh').textContent = 'Đang tải…'; render(runner);
  try {
    const data = await request('/api/xp');
    $('xp').textContent = Number(data.xp).toLocaleString('vi-VN');
    $('xp-detail').textContent = `${data.day} · Giờ Việt Nam`;
    $('sessions').textContent = data.sessions == null ? 'Toàn tài khoản trung' : `${data.sessions} phiên học`;
    $('xp-message').textContent = 'Dữ liệu máy chủ có thể cập nhật chậm.';
    log(`XP hôm nay: ${data.xp} XP.`); notice('');
  } catch (error) {
    $('xp').textContent = '—'; $('xp-detail').textContent = 'Chưa xác định được XP';
    $('sessions').textContent = 'Toàn tài khoản trung';
    $('xp-message').textContent = error.message; log(error.message);
  } finally { loading = false; $('refresh').textContent = '↻ Làm mới'; render(runner); }
});
$('settings-open').addEventListener('click', () => dialog.showModal());
$('settings-close').addEventListener('click', () => dialog.close());
$('settings-form').addEventListener('submit', event => {
  event.preventDefault();
  try {
    if (runner.running || loading) throw new Error('Chờ tác vụ hiện tại hoàn tất.');
    const nextToken = $('token').value.trim() || token;
    const parts = nextToken.split('.');
    if (parts.length !== 3) throw new Error('Token không đúng định dạng JWT.');
    const payload = JSON.parse(atob(parts[1].replaceAll('-', '+').replaceAll('_', '/')));
    if (String(payload.sub) !== '787468231') throw new Error('Token phải thuộc tài khoản trung.');
    let base = $('api-base').value.trim().replace(/\/$/, '');
    if (base) {
      const url = new URL(base);
      if (url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error('URL API chỉ gồm https://tên-miền, không có đường dẫn.');
      if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost','127.0.0.1'].includes(url.hostname))) throw new Error('Máy chủ online phải dùng HTTPS.');
      base = url.origin;
    }
    token = nextToken; apiBase = base;
    try { localStorage.setItem('duo-api-base', base); } catch {}
    $('token').value = ''; $('settings-error').textContent = '';
    $('xp').textContent = '—'; $('xp-detail').textContent = 'Sẵn sàng tải dữ liệu';
    $('xp-message').textContent = 'Đã kết nối token trung. Bấm Làm mới để xem XP.';
    notice(''); dialog.close(); render(runner); log('Đã lưu kết nối cho phiên hiện tại.');
  } catch (error) { $('settings-error').textContent = error.message || 'Thông tin kết nối không hợp lệ.'; }
});
$('forget').addEventListener('click', () => {
  if (runner.running || loading) return;
  token = ''; $('token').value = ''; $('xp').textContent = '—';
  $('xp-detail').textContent = 'Chưa tải dữ liệu hôm nay'; $('sessions').textContent = 'Toàn tài khoản trung';
  $('xp-message').textContent = 'Đã xóa token. Nhập lại để dùng.';
  $('settings-error').textContent = ''; dialog.close(); render(runner); log('Đã xóa token khỏi phiên hiện tại.');
});
$('clear-log').addEventListener('click', () => { $('logs').replaceChildren(); });
document.addEventListener('visibilitychange', () => {
  if (document.hidden && runner.running && !runner.paused) {
    runner.pause(true); log('Tự tạm dừng khi rời trang. Bấm Tiếp tục khi quay lại.');
  }
});
window.addEventListener('beforeunload', event => {
  if (runner.running) { event.preventDefault(); event.returnValue = ''; }
});
render(runner);
if (location.hostname.endsWith('.github.io') && !apiBase) notice('Giao diện đang ở GitHub Pages. Nhập URL máy chủ Render trong Cài đặt để chạy điểm và xem XP.');
