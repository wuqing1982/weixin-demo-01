const assert = require('assert');
const fs = require('fs');
const path = require('path');

const templatePath = path.join(__dirname, '..', 'pages', 'login', 'index.wxml');
const scriptPath = path.join(__dirname, '..', 'pages', 'login', 'index.js');

const template = fs.readFileSync(templatePath, 'utf8');
const script = fs.readFileSync(scriptPath, 'utf8');

assert(
  template.includes('open-type="chooseAvatar"') && template.includes('bindchooseavatar="onChooseAvatar"'),
  'login page should expose a chooseAvatar button for syncing the avatar'
);

assert(
  template.includes('type="nickname"') && template.includes('bindinput="onProfileNicknameInput"'),
  'login page should expose a nickname input for syncing the display name'
);

assert(
  template.includes('保存头像昵称'),
  'login page should provide an explicit save action for avatar and nickname'
);

assert(
  !script.includes('wx.getUserProfile'),
  'login page should not rely on wx.getUserProfile for avatar and nickname sync'
);

console.log('login profile sync ui tests passed');
