import test from 'node:test';
import assert from 'node:assert/strict';
import {Runner} from './public/runner.js';
const tick = () => new Promise(resolve => setTimeout(resolve, 5));

test('runs sequentially and completes requested count', async () => {
  let count = 0, active = false;
  const runner = new Runner({send:async () => { assert.equal(active,false); active=true; await tick(); count++; active=false; }, onChange:()=>{}, onLog:()=>{}});
  await runner.start(3,0);
  assert.equal(count,3); assert.equal(runner.accepted,3); assert.equal(runner.running,false);
});
test('pause in flight, resume then stop prevents later requests', async () => {
  let release, calls=0;
  const pending = new Promise(resolve => { release=resolve; });
  const runner = new Runner({send:async () => { calls++; if(calls===1) await pending; }, onChange:()=>{}, onLog:()=>{}, sleep:tick});
  const result = runner.start(10,0);
  await tick(); runner.pause(true); release(); await tick();
  assert.equal(calls,1);
  runner.pause(false); runner.stop(); await result;
  assert.equal(calls,1); assert.equal(runner.running,false);
});
test('errors stop without retry', async () => {
  let calls=0;
  const runner = new Runner({send:async()=>{calls++;throw new Error('mock');},onChange:()=>{},onLog:()=>{}});
  await runner.start(20,0); assert.equal(calls,1); assert.equal(runner.status,'Đã dừng do lỗi');
});
test('second start cannot create concurrent loop', async () => {
  let release,calls=0;
  const pending=new Promise(resolve=>{release=resolve;});
  const runner=new Runner({send:async()=>{calls++;await pending;},onChange:()=>{},onLog:()=>{}});
  const first=runner.start(1,0); await tick(); await runner.start(9,0); release(); await first;
  assert.equal(calls,1);
});
