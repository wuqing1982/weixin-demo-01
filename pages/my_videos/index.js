const { updateNavBar } = require('../../shared/theme-helper');
const { getMyVideoExports } = require('../../services/scene');
const { getConfig } = require('../../services/config');

Page({
  data: {
    theme: 'dark',
    loading: true,
    videos: [],
    errorMessage: ''
  },

  onShow() {
    const theme = getApp().globalData.theme;
    this.setData({ theme });
    updateNavBar(theme);
    this.loadVideos();
  },

  onPullDownRefresh() {
    this.loadVideos().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  async loadVideos() {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const data = await getMyVideoExports();
      const list = (data.items || []).map(item => {
        if (item.videoUrl && !item.videoUrl.startsWith('http')) {
          const { staticBaseUrl } = getConfig();
          item.videoUrl = staticBaseUrl + item.videoUrl;
        }
        if (item.coverUrl && !item.coverUrl.startsWith('http')) {
          const { staticBaseUrl } = getConfig();
          item.coverUrl = staticBaseUrl + item.coverUrl;
        }
        return item;
      });
      this.setData({ loading: false, videos: list });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '视频列表加载失败'
      });
    }
  },

  onPlayVideo(event) {
    const { index } = event.currentTarget.dataset;
    const video = this.data.videos[index];
    if (!video || !video.videoUrl) {
      wx.showToast({ title: '视频地址无效', icon: 'none' });
      return;
    }

    wx.showActionSheet({
      itemList: ['保存到相册'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this._downloadAndSave(video.videoUrl);
        }
      }
    });
  },

  _downloadAndSave(videoUrl) {
    wx.showLoading({ title: '下载中...', mask: true });
    const downloadTask = wx.downloadFile({
      url: videoUrl,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.saveVideoToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.hideLoading();
              wx.showToast({ title: '已保存到相册', icon: 'success' });
            },
            fail: (err) => {
              wx.hideLoading();
              const errMsg = (err && err.errMsg) || '';
              if (errMsg.indexOf('auth deny') !== -1 || errMsg.indexOf('authorize') !== -1) {
                wx.showModal({
                  title: '需要授权',
                  content: '请在设置中允许访问相册后重试。',
                  confirmText: '去设置',
                  success: (modalRes) => {
                    if (modalRes.confirm) { wx.openSetting(); }
                  }
                });
              } else {
                wx.showModal({ title: '保存失败', content: errMsg || '请重试', showCancel: false });
              }
            }
          });
        } else {
          wx.hideLoading();
          wx.showToast({ title: '下载失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '下载失败，请检查网络', icon: 'none' });
      }
    });
    downloadTask.onProgressUpdate((res) => {
      wx.showLoading({ title: `下载 ${res.progress}%`, mask: true });
    });
  }
});
