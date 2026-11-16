// Execute the actual controller with a small DOM fixture; no browser dependency.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const site = '/amax/home/fengshuangyu/cvrgs/ExgsPage/cvrgs.github.io';
const assert = require('assert');
const makeElement = (extra = {}) => Object.assign({
  listeners: {}, dataset: {}, hidden: false,
  addEventListener(type, cb) { this.listeners[type] = cb; },
  classList: { toggle() {} },
  setAttribute(key, value) { this[key] = value; },
}, extra);
function fixture(kind, scenes) {
  const video = makeElement({paused: true, playCalls: 0,
    pause() {this.paused = true;}, load() {},
    play() {this.paused = false; this.playCalls++; return Promise.resolve();}});
  const buttons = scenes.map(scene => makeElement({dataset: {scene}}));
  const elements = {
    'video': video,
    '[data-version]': makeElement({value: 'v2'}),
    '[data-setting]': kind === 'hdr' ? makeElement({value: '50U50O'}) : null,
    '[data-setting-control]': makeElement(),
    '[data-download]': makeElement(), '[data-protocol]': makeElement(),
    '[data-caption]': makeElement(), '[data-video-error]': makeElement(),
    '[data-scene][aria-pressed="true"]': buttons[0],
  };
  return {
    dataset: {comparisonGroup: kind, caption: 'updated', legacyCaption: 'previous'},
    buttons, elements,
    querySelector(selector) {assert(selector in elements, selector); return elements[selector];},
    querySelectorAll(selector) {assert.equal(selector, '[data-scene]'); return buttons;},
  };
}
const groups = [fixture('hdr', ['box', 'luckycat', 'flower', 'plant']),
                fixture('syn', ['hotdog', 'ficus', 'mic', 'chair'])];
const document = {
  addEventListener(type, cb) {assert.equal(type, 'DOMContentLoaded'); cb();},
  querySelectorAll(selector) {assert.equal(selector, '[data-comparison-group]'); return groups;},
};
vm.runInNewContext(fs.readFileSync(path.join(site, 'static/js/comparisons-v2.js'), 'utf8'), {document});
let checks = 0;
for (const group of groups) {
  const e = group.elements;
  for (const button of group.buttons) {
    button.listeners.click();
    const settings = e['[data-setting]'] ? ['12U12M100O', '100U12M12O', '33U33M33O', '50U50O'] : [null];
    for (const setting of settings) {
      if (setting) {e['[data-setting]'].value = setting; e['[data-setting]'].listeners.change();}
      const video = e.video;
      assert(fs.existsSync(path.join(site, video.src)), video.src);
      assert(fs.existsSync(path.join(site, video.poster)), video.poster);
      assert(fs.existsSync(path.join(site, e['[data-protocol]'].href)));
      assert.equal(e['[data-download]'].href, video.src);
      assert.equal(e['[data-protocol]'].hidden, false);
      assert.equal(e['[data-caption]'].textContent, 'updated');
      assert.equal(video.paused, true);
      checks++;
    }
    e.video.paused = false;
    e['[data-version]'].value = 'legacy';
    e['[data-version]'].listeners.change();
    assert(fs.existsSync(path.join(site, e.video.src)), e.video.src);
    assert.equal(e['[data-protocol]'].hidden, true);
    assert.equal(e['[data-caption]'].textContent, 'previous');
    assert.equal(e.video.paused, false);
    if (e['[data-setting]']) assert.equal(e['[data-setting-control]'].hidden, true);
    e.video.listeners.error();
    assert.equal(e['[data-video-error]'].hidden, false);
    e['[data-version]'].value = 'v2';
    e['[data-version]'].listeners.change();
    assert.equal(e['[data-video-error]'].hidden, true);
    if (e['[data-setting]']) assert.equal(e['[data-setting-control]'].hidden, false);
    e.video.pause();
    checks++;
  }
}
console.log(JSON.stringify({updated_and_legacy_switch_checks: checks, passed: true,
  playback_state_preserved: true, error_reset_checked: true,
  scope: 'actual JavaScript controller with DOM fixture; not an end-to-end browser playback test'}));
