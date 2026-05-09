const { bindPhone } = require('../../services/user');

Component({
  properties: {
    visible: {
      type: Boolean,
      value: false,
    },
    title: {
      type: String,
      value: '绑定手机号，获取全部权益',
    },
    description: {
      type: String,
      value: '绑定手机号后即可使用视频导出等全部会员功能',
    },
    theme: {
      type: String,
      value: 'dark',
    },
  },

  data: {
    binding: false,
  },

  methods: {
    async onGetPhoneNumber(e) {
      if (e.detail.errMsg !== 'getPhoneNumber:ok') {
        return;
      }

      this.setData({ binding: true });
      try {
        const result = await bindPhone(e.detail.code);
        const app = getApp();
        if (app.globalData.currentUser) {
          app.globalData.currentUser.mobileVerified = true;
          app.globalData.currentUser.mobile = result.mobile;
        }
        this.triggerEvent('bindsuccess', { maskedMobile: result.mobile });
      } catch (err) {
        const msg = (err && (err.message || err.errMsg)) || '绑定失败';
        wx.showToast({ title: msg, icon: 'none', duration: 3000 });
      } finally {
        this.setData({ binding: false });
      }
    },

    onClose() {
      this.triggerEvent('close');
    },

    onMaskTap() {
      this.triggerEvent('close');
    },

    noop() {},
  },
});
