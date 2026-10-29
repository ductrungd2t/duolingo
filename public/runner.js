export class Runner {
  constructor({send, onChange, onLog, sleep = ms => new Promise(resolve => setTimeout(resolve, ms))}) {
    Object.assign(this, {send, onChange, onLog, sleep});
    this.running = false; this.paused = false; this.stopping = false; this.accepted = 0;
  }
  changed(status) { this.status = status; this.onChange(this); }
  pause(value = !this.paused) {
    if (!this.running || this.stopping) return;
    this.paused = value;
    this.changed(value ? 'Tạm dừng sau yêu cầu đang gửi' : 'Đang tiếp tục');
    this.onLog(value ? 'Đã yêu cầu tạm dừng.' : 'Tiếp tục chạy.');
  }
  stop() { if (this.running) { this.stopping = true; this.changed('Đang dừng…'); } }
  async ready() {
    while (this.paused && !this.stopping) await this.sleep(150);
    return !this.stopping;
  }
  async start(count, interval) {
    if (this.running) return;
    this.running = true; this.paused = false; this.stopping = false;
    this.accepted = 0; this.total = count;
    this.changed('Đang chạy');
    let failure = false;
    try {
      for (let i = 0; i < count; i++) {
        if (!(await this.ready())) break;
        this.changed(`Đang gửi lượt ${i + 1}/${count}`);
        await this.send();
        this.accepted++;
        this.onLog(`Lượt ${this.accepted}/${count}: HTTP thành công; chưa xác nhận XP tăng.`);
        this.changed(this.paused ? 'Đã tạm dừng' : 'Đang chạy');
        if (i + 1 < count) {
          let remaining = interval * 1000;
          while (remaining > 0 && await this.ready()) {
            const slice = Math.min(remaining, 150);
            await this.sleep(slice); remaining -= slice;
          }
        }
      }
    } catch (error) { failure = true; this.onLog(error.message || 'Yêu cầu thất bại.'); }
    finally {
      this.running = false; this.paused = false;
      this.changed(failure ? 'Đã dừng do lỗi' : this.stopping ? 'Đã dừng' : 'Đã hoàn tất');
      this.onLog(`${this.status} · ${this.accepted} phản hồi HTTP thành công.`);
    }
  }
}
