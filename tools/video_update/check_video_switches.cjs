// Check the published scene/method controls and their real media assets.
// This exercises the actual controller without a browser or media decoder.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const site = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(site, 'index.html'), 'utf8');
const element = (extra = {}) => Object.assign({
  listeners: {}, dataset: {}, hidden: false, attributes: {},
  addEventListener(type, cb) { this.listeners[type] = cb; },
  setAttribute(key, value) { this.attributes[key] = value; },
  getAttribute(key) { return this.attributes[key]; },
  removeAttribute(key) { delete this[key]; },
}, extra);
const attr = (tag, name) => tag.match(new RegExp(`${name}="([^"]*)"`))?.[1];
const groups = [...html.matchAll(/<section[^>]*data-comparison-group="([^"]+)"[^>]*>([\s\S]*?)<\/section>/g)].map(([, kind, body]) => {
  const buttons = [...body.matchAll(/<button\b[^>]*>/g)].map(([tag]) => {
    const scene = attr(tag, 'data-scene');
    const method = attr(tag, 'data-method');
    return element({dataset: scene ? {scene} : {method}, attributes: {'aria-pressed': attr(tag, 'aria-pressed')}});
  });
  const videoTag = body.match(/<video\b[^>]*>/)[0];
  const video = element({src: attr(videoTag, 'src'), poster: attr(videoTag, 'poster'), paused: true,
    pause() { this.paused = true; }, load() {},
    play() { this.paused = false; return Promise.resolve(); }});
  const download = element({href: attr(body.match(/<a data-download[^>]*>/)[0], 'href')});
  const error = element({hidden: true});
  return {
    dataset: {comparisonGroup: kind}, buttons, video, download, error,
    querySelector(selector) {
      if (selector === 'video') return video;
      if (selector === '[data-download]') return download;
      if (selector === '[data-video-error]') return error;
      const choice = selector.match(/^\[data-(scene|method)\]\[aria-pressed="true"\]$/)?.[1];
      assert(choice, selector);
      return buttons.find(button => button.dataset[choice] && button.getAttribute('aria-pressed') === 'true') ?? null;
    },
    querySelectorAll(selector) {
      const choice = selector.match(/^\[data-(scene|method)\]$/)?.[1];
      assert(choice, selector);
      return buttons.filter(button => button.dataset[choice]);
    },
  };
});
assert.equal(groups.length, 4);
const document = {
  addEventListener(type, cb) { assert.equal(type, 'DOMContentLoaded'); cb(); },
  querySelectorAll(selector) { assert.equal(selector, '[data-comparison-group]'); return groups; },
};
vm.runInNewContext(fs.readFileSync(path.join(site, 'static/js/comparisons-v2.js'), 'utf8'), {document});
let combinations = 0;
for (const group of groups) {
  const verifyMedia = () => {
    assert(fs.existsSync(path.join(site, group.video.src)), group.video.src);
    if (group.video.poster) assert(fs.existsSync(path.join(site, group.video.poster)), group.video.poster);
    assert.equal(group.download.href, group.video.src);
    for (const choice of ['scene', 'method']) {
      const choices = group.querySelectorAll(`[data-${choice}]`);
      if (choices.length) assert.equal(choices.filter(x => x.getAttribute('aria-pressed') === 'true').length, 1);
    }
  };
  verifyMedia(); // HTML defaults must work before JavaScript interaction.
  for (const scene of group.querySelectorAll('[data-scene]')) {
    scene.listeners.click();
    const methods = group.querySelectorAll('[data-method]');
    for (const method of methods.length ? methods : [null]) {
      if (method) method.listeners.click();
      verifyMedia();
      assert(group.video.src.includes(`_${scene.dataset.scene}`));
      if (method) assert(group.video.src.includes(`_${method.dataset.method}_path`));
      assert.equal(group.video.paused, true);
      combinations++;
    }
  }
  group.video.paused = false;
  group.querySelectorAll('[data-scene]')[0].listeners.click();
  assert.equal(group.video.paused, false, 'Playing state must persist through a scene switch');
  group.video.listeners.error();
  assert.equal(group.error.hidden, false);
  group.querySelectorAll('[data-scene]')[1].listeners.click();
  assert.equal(group.error.hidden, true);
  group.video.listeners.error();
  group.video.listeners.loadeddata();
  assert.equal(group.error.hidden, true);
  verifyMedia();
}
assert(!/Previous video|Updated methods|data-version|data-protocol|xxxx\.xxxxx|Anonymous Author/.test(html));
const authors = html.split('class="publication-authors"')[1].split('</div>')[0];
assert(!authors.includes('<a '));
console.log(JSON.stringify({dataset_sections: groups.length, scene_method_combinations: combinations,
  asset_paths_valid: true, playback_state_preserved: true, error_recovery_checked: true,
  historical_controls_removed: true, passed: true}));
