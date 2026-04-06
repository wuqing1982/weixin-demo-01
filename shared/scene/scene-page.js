const { saveSceneHotspots } = require('../../services/scene');
const {
  normalizeEditorRect,
  applyMoveDelta,
  applyResizeDelta,
  normalizeFloatingButtonPosition,
  applyFloatingButtonDelta
} = require('./hotspot-editor');
const { getSceneNeighbors } = require('./scene-registry');

const SWIPE_DISTANCE = 70;
const SWIPE_VERTICAL_TOLERANCE = 80;
const DEFAULT_TITLE = '英语场景';
const DEFAULT_SAVE_BUTTON_POSITION = {
  left: 10,
  top: 80
};

function findEntryById(entries, id) {
  return (entries || []).find((entry) => entry.id === id) || null;
}

function cloneEntries(entries) {
  return JSON.parse(JSON.stringify(entries || []));
}

function normalizeEntry(entry) {
  if (!entry) {
    return null;
  }

  return Object.assign({}, entry, {
    sentenceTranslation: entry.sentenceTranslation || entry.sentence_translation || '',
    rect: entry.rect ? normalizeEditorRect(entry.rect) : null
  });
}

function buildNavigation(sceneId, sceneTabs) {
  if (sceneTabs && sceneTabs.length) {
    const index = sceneTabs.findIndex((item) => item.sceneId === sceneId);
    return {
      prevScene: index > 0 ? sceneTabs[index - 1] : null,
      nextScene: index >= 0 && index < sceneTabs.length - 1 ? sceneTabs[index + 1] : null,
      sceneTabs
    };
  }

  if (!sceneId) {
    return {
      prevScene: null,
      nextScene: null,
      sceneTabs: []
    };
  }

  return getSceneNeighbors(sceneId);
}

function buildSceneState(sceneData) {
  const safeSceneData = sceneData || {};
  const navigation = buildNavigation(safeSceneData.sceneId || '', safeSceneData.sceneTabs || null);

  return {
    sceneId: safeSceneData.sceneId || '',
    title: safeSceneData.title || '',
    background: safeSceneData.background || '',
    items: (safeSceneData.items || []).map(normalizeEntry).filter(Boolean),
    verbs: (safeSceneData.verbs || []).map(normalizeEntry).filter(Boolean),
    prevScene: navigation.prevScene,
    nextScene: navigation.nextScene,
    sceneTabs: navigation.sceneTabs,
    capabilities: safeSceneData.capabilities || {},
    canEditHotspots: !!(safeSceneData.capabilities && safeSceneData.capabilities.canEditHotspots)
  };
}

function createScenePage(sceneData) {
  const initialState = buildSceneState(sceneData);

  return {
    data: {
      sceneId: initialState.sceneId,
      title: initialState.title,
      background: initialState.background,
      items: initialState.items,
      hotspotItems: initialState.items,
      draftItems: [],
      verbs: initialState.verbs,
      activeId: '',
      activeType: '',
      activeEntry: null,
      prevScene: initialState.prevScene,
      nextScene: initialState.nextScene,
      sceneTabs: initialState.sceneTabs,
      capabilities: initialState.capabilities,
      canEditHotspots: initialState.canEditHotspots,
      editorMode: false,
      editingItemId: '',
      editingEntry: null,
      isDirty: false,
      isSaving: false,
      isDraggingSaveHandle: false,
      saveButtonPosition: normalizeFloatingButtonPosition(DEFAULT_SAVE_BUTTON_POSITION),
      deviceMode: 'mobile',
      playbackRate: 1.0,
      isLooping: false,
      loading: !initialState.sceneId,
      errorMessage: ''
    },

    initializeScenePage() {
      if (this.scenePageInitialized) {
        return;
      }

      this.scenePageInitialized = true;
      this.stageMetrics = null;
      this.dragState = null;
      this.saveButtonDragState = null;
      this.viewportRect = this.getViewportRect();

      wx.setNavigationBarTitle({
        title: this.data.title || DEFAULT_TITLE
      });

      this.audioContext = wx.createInnerAudioContext();
      this.audioContext.obeyMuteSwitch = false;
      this.audioContext.onError(() => {
        wx.showToast({
          title: '音频播放失败',
          icon: 'none'
        });
      });

      try {
        const savedRate = wx.getStorageSync('preferredPlaybackRate');
        if (savedRate) {
          this.setData({
            playbackRate: parseFloat(savedRate) || 1.0
          });
        }
      } catch (error) {
        console.log('读取播放速度失败', error);
      }
    },

    onLoad() {
      this.initializeScenePage();
    },

    onHide() {
      this.stopAudio();
    },

    onUnload() {
      this.dragState = null;
      this.saveButtonDragState = null;
      this.destroyAudio();
    },

    setupScene(nextSceneData) {
      const nextState = buildSceneState(nextSceneData);
      this.setData({
        sceneId: nextState.sceneId,
        title: nextState.title,
        background: nextState.background,
        items: nextState.items,
        hotspotItems: nextState.items,
        draftItems: [],
        verbs: nextState.verbs,
        prevScene: nextState.prevScene,
        nextScene: nextState.nextScene,
        sceneTabs: nextState.sceneTabs,
        capabilities: nextState.capabilities,
        canEditHotspots: nextState.canEditHotspots,
        editorMode: false,
        editingItemId: '',
        editingEntry: null,
        isDirty: false,
        isSaving: false,
        isDraggingSaveHandle: false,
        saveButtonPosition: normalizeFloatingButtonPosition(DEFAULT_SAVE_BUTTON_POSITION, this.viewportRect),
        activeId: '',
        activeType: '',
        activeEntry: null,
        loading: false,
        errorMessage: ''
      });
      this.stageMetrics = null;
      this.dragState = null;
      this.saveButtonDragState = null;

      wx.setNavigationBarTitle({
        title: nextState.title || DEFAULT_TITLE
      });
    },

    setLoadError(message) {
      this.setData({
        loading: false,
        errorMessage: message || '场景加载失败'
      });
    },

    onTouchStart(event) {
      if (this.data.editorMode) {
        return;
      }

      const touch = event.changedTouches && event.changedTouches[0];
      if (!touch) {
        return;
      }

      this.touchStartPoint = {
        x: touch.pageX,
        y: touch.pageY
      };
    },

    onTouchEnd(event) {
      if (this.data.editorMode) {
        return;
      }

      const touch = event.changedTouches && event.changedTouches[0];
      const start = this.touchStartPoint;

      this.touchStartPoint = null;

      if (!touch || !start) {
        return;
      }

      const deltaX = touch.pageX - start.x;
      const deltaY = touch.pageY - start.y;

      if (Math.abs(deltaY) > SWIPE_VERTICAL_TOLERANCE || Math.abs(deltaX) < SWIPE_DISTANCE) {
        return;
      }

      if (deltaX < 0) {
        this.navigateToScene(this.data.nextScene);
        return;
      }

      this.navigateToScene(this.data.prevScene);
    },

    onTapHotspot(event) {
      const { id } = event.currentTarget.dataset;
      const item = findEntryById(this.data.editorMode ? this.data.draftItems : this.data.items, id);

      if (!item) {
        return;
      }

      if (this.data.editorMode) {
        this.selectEditingItem(item.id);
        return;
      }

      this.activateEntry(item, 'item');
    },

    onTapVerb(event) {
      if (this.data.editorMode) {
        return;
      }

      const { id } = event.currentTarget.dataset;
      const verb = findEntryById(this.data.verbs, id);

      if (!verb) {
        return;
      }

      this.activateEntry(verb, 'verb');
    },

    onCloseOverlay() {
      this.stopAudio();
      this.setData({
        activeId: '',
        activeType: '',
        activeEntry: null
      });
    },

    onTapPrevScene() {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }
      this.navigateToScene(this.data.prevScene);
    },

    onTapNextScene() {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }
      this.navigateToScene(this.data.nextScene);
    },

    onTapScenePill(event) {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      const { sceneId } = event.currentTarget.dataset;
      const targetScene = this.data.sceneTabs.find((item) => item.sceneId === sceneId);
      this.navigateToScene(targetScene);
    },

    onRateChange(event) {
      const rate = parseFloat(event.detail.value);
      this.setData({
        playbackRate: rate
      });
      try {
        wx.setStorageSync('preferredPlaybackRate', rate.toString());
      } catch (error) {
        console.log('保存播放速度失败', error);
      }
    },

    onRatePreset(event) {
      const { rate } = event.currentTarget.dataset;
      const rateValue = parseFloat(rate);
      this.setData({
        playbackRate: rateValue
      });
      try {
        wx.setStorageSync('preferredPlaybackRate', rate);
      } catch (error) {
        console.log('保存播放速度失败', error);
      }
      wx.showToast({
        title: rateValue < 1 ? '慢速播放' : '快速播放',
        icon: 'none',
        duration: 800
      });
    },

    onToggleLoop() {
      const newLoopState = !this.data.isLooping;
      this.setData({
        isLooping: newLoopState
      });
      wx.showToast({
        title: newLoopState ? '循环播放已开启' : '循环播放已关闭',
        icon: 'none',
        duration: 1200
      });
    },

    onOpenCamera() {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      wx.navigateTo({
        url: '/pages/create_scene/index'
      });
    },

    onExportVideo() {
      wx.showModal({
        title: '🎬 导出视频',
        content: '视频导出功能开发中...\n\n将支持：\n• 场景学习记录导出\n• 带配音的视频生成\n• 分享到朋友圈',
        showCancel: false,
        confirmText: '知道了'
      });
    },

    activateEntry(entry, type) {
      this.setData({
        activeId: entry.id,
        activeType: type,
        activeEntry: entry
      });

      this.playAudio(entry);
    },

    navigateToScene(scene) {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      if (!scene || !scene.sceneId || scene.sceneId === this.data.sceneId) {
        return;
      }

      this.stopAudio();
      wx.redirectTo({
        url: scene.route || `/pages/scene_runtime/index?sceneId=${scene.sceneId}`
      });
    },

    playAudio(entry) {
      if (!this.audioContext || !entry.audio) {
        wx.showToast({
          title: '使用在线语音...',
          icon: 'none',
          duration: 1000
        });
        this.simulateTTS(entry);
        return;
      }

      this.audioContext.playbackRate = this.data.playbackRate;
      this.audioContext.stop();
      this.audioContext.src = entry.audio;
      this.audioContext.play();

      if (this.data.isLooping) {
        this.audioContext.onEnded(() => {
          if (this.data.isLooping && this.data.activeId === entry.id) {
            setTimeout(() => {
              this.audioContext.play();
            }, 500);
          }
        });
      }
    },

    simulateTTS(entry) {
      const { getTtsUrl } = require('../../services/scene');
      const text = entry.sentence || entry.word || '';
      if (!text) {
        return;
      }
      const ttsUrl = getTtsUrl(text);
      if (this.ttsAudioContext) {
        this.ttsAudioContext.stop();
        this.ttsAudioContext.destroy();
      }
      this.ttsAudioContext = wx.createInnerAudioContext();
      this.ttsAudioContext.obeyMuteSwitch = false;
      this.ttsAudioContext.onError((err) => {
        console.log('TTS audio error', err);
      });
      this.ttsAudioContext.src = ttsUrl;
      this.ttsAudioContext.play();
    },

    showEditorToast(message) {
      wx.showToast({
        title: message || '请先保存或退出编辑',
        icon: 'none',
        duration: 1200
      });
    },

    measureStageRect() {
      return new Promise((resolve) => {
        wx.nextTick(() => {
          this.createSelectorQuery()
            .select('#sceneContent')
            .boundingClientRect((rect) => {
              this.stageMetrics = rect || null;
              resolve(rect || null);
            })
            .exec();
        });
      });
    },

    selectEditingItem(itemId) {
      const entry = findEntryById(this.data.draftItems, itemId);
      if (!entry) {
        return;
      }

      this.setData({
        editingItemId: entry.id,
        editingEntry: entry,
        activeId: '',
        activeType: '',
        activeEntry: null
      });
    },

    getViewportRect() {
      try {
        if (typeof wx.getWindowInfo === 'function') {
          const info = wx.getWindowInfo();
          return {
            width: info.windowWidth || 375,
            height: info.windowHeight || 667
          };
        }
        const info = wx.getSystemInfoSync();
        return {
          width: info.windowWidth || 375,
          height: info.windowHeight || 667
        };
      } catch (error) {
        return {
          width: 375,
          height: 667
        };
      }
    },

    async enterEditorMode() {
      if (!this.data.canEditHotspots || this.data.loading || this.data.isSaving) {
        return;
      }

      if (this.data.editorMode) {
        return;
      }

      const draftItems = cloneEntries(this.data.items);
      const firstItem = draftItems[0] || null;
      this.stopAudio();
      this.setData({
        editorMode: true,
        draftItems,
        hotspotItems: draftItems,
        editingItemId: firstItem ? firstItem.id : '',
        editingEntry: firstItem,
        isDirty: false,
        activeId: '',
        activeType: '',
        activeEntry: null
      });
      this.viewportRect = this.getViewportRect();
      this.setData({
        saveButtonPosition: normalizeFloatingButtonPosition(
          this.data.saveButtonPosition || DEFAULT_SAVE_BUTTON_POSITION,
          this.viewportRect
        )
      });
      await this.measureStageRect();
    },

    exitEditorMode() {
      if (!this.data.editorMode) {
        return;
      }

      if (!this.data.isDirty) {
        this.setData({
          editorMode: false,
          draftItems: [],
          hotspotItems: this.data.items,
          editingItemId: '',
          editingEntry: null
        });
        this.dragState = null;
        this.saveButtonDragState = null;
        return;
      }

      wx.showModal({
        title: '放弃未保存改动？',
        content: '当前热点位置还没有保存，退出后会丢失这些修改。',
        success: (result) => {
          if (!result.confirm) {
            return;
          }

          this.setData({
            editorMode: false,
            draftItems: [],
            hotspotItems: this.data.items,
            editingItemId: '',
            editingEntry: null,
            isDirty: false
          });
          this.dragState = null;
          this.saveButtonDragState = null;
        }
      });
    },

    async onEnterEditorMode() {
      await this.enterEditorMode();
    },

    onExitEditorMode() {
      this.exitEditorMode();
    },

    updateDraftRect(itemId, rect, options = {}) {
      const nextDraftItems = cloneEntries(this.data.draftItems);
      const index = nextDraftItems.findIndex((item) => item.id === itemId);

      if (index < 0) {
        return;
      }

      nextDraftItems[index].rect = normalizeEditorRect(rect);
      const editingEntry = nextDraftItems[index];
      this.setData({
        draftItems: nextDraftItems,
        hotspotItems: nextDraftItems,
        editingItemId: itemId,
        editingEntry,
        isDirty: options.markDirty === false ? this.data.isDirty : true
      });
    },

    onEditorZoneTouchStart(event) {
      if (!this.data.editorMode || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      const { id } = event.currentTarget.dataset;
      const item = findEntryById(this.data.draftItems, id);

      if (!touch || !item || !item.rect) {
        return;
      }

      this.selectEditingItem(id);
      this.dragState = {
        itemId: id,
        mode: 'move',
        startX: touch.pageX,
        startY: touch.pageY,
        startRect: Object.assign({}, item.rect)
      };
    },

    onEditorHandleTouchStart(event) {
      if (!this.data.editorMode || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      const { id, handle } = event.currentTarget.dataset;
      const item = findEntryById(this.data.draftItems, id);

      if (!touch || !item || !item.rect || !handle) {
        return;
      }

      this.selectEditingItem(id);
      this.dragState = {
        itemId: id,
        mode: 'resize',
        handle,
        startX: touch.pageX,
        startY: touch.pageY,
        startRect: Object.assign({}, item.rect)
      };
    },

    onEditorZoneTouchMove(event) {
      if (!this.data.editorMode || !this.dragState || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      const metrics = this.stageMetrics;

      if (!touch || !metrics || !metrics.width || !metrics.height) {
        return;
      }

      const deltaX = ((touch.pageX - this.dragState.startX) / metrics.width) * 100;
      const deltaY = ((touch.pageY - this.dragState.startY) / metrics.height) * 100;
      const nextRect = this.dragState.mode === 'resize'
        ? applyResizeDelta(this.dragState.startRect, this.dragState.handle, deltaX, deltaY)
        : applyMoveDelta(this.dragState.startRect, deltaX, deltaY);
      this.updateDraftRect(this.dragState.itemId, nextRect);
    },

    onEditorZoneTouchEnd() {
      this.dragState = null;
    },

    onSaveButtonTouchStart(event) {
      if (!this.data.editorMode || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      if (!touch) {
        return;
      }

      this.saveButtonDragState = {
        startX: touch.pageX,
        startY: touch.pageY,
        startPosition: Object.assign({}, this.data.saveButtonPosition)
      };
      this.setData({
        isDraggingSaveHandle: true
      });
    },

    onSaveButtonTouchMove(event) {
      if (!this.data.editorMode || !this.saveButtonDragState || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      if (!touch) {
        return;
      }

      const deltaX = touch.pageX - this.saveButtonDragState.startX;
      const deltaY = touch.pageY - this.saveButtonDragState.startY;
      this.viewportRect = this.viewportRect || this.getViewportRect();
      const nextPosition = applyFloatingButtonDelta(
        this.saveButtonDragState.startPosition,
        deltaX,
        deltaY,
        this.viewportRect
      );

      this.setData({
        saveButtonPosition: nextPosition
      });
    },

    onSaveButtonTouchEnd() {
      this.saveButtonDragState = null;
      if (this.data.isDraggingSaveHandle) {
        this.setData({
          isDraggingSaveHandle: false
        });
      }
    },

    onSaveButtonTouchCancel() {
      this.onSaveButtonTouchEnd();
    },

    onTapFloatingSave() {
      this.onSaveHotspots();
    },

    onEditorNudge(event) {
      if (!this.data.editorMode || !this.data.editingItemId || this.data.isSaving) {
        return;
      }

      const item = findEntryById(this.data.draftItems, this.data.editingItemId);
      if (!item || !item.rect) {
        return;
      }

      const { dl, dt, dw, dh } = event.currentTarget.dataset;
      this.updateDraftRect(item.id, {
        l: item.rect.l + (parseFloat(dl) || 0),
        t: item.rect.t + (parseFloat(dt) || 0),
        w: item.rect.w + (parseFloat(dw) || 0),
        h: item.rect.h + (parseFloat(dh) || 0)
      });
    },

    onEditorResetCurrent() {
      if (!this.data.editorMode || !this.data.editingItemId || this.data.isSaving) {
        return;
      }

      const sourceItem = findEntryById(this.data.items, this.data.editingItemId);
      if (!sourceItem || !sourceItem.rect) {
        return;
      }

      this.updateDraftRect(sourceItem.id, sourceItem.rect);
    },

    async onSaveHotspots() {
      if (!this.data.editorMode || !this.data.isDirty || this.data.isSaving) {
        return;
      }

      this.setData({
        isSaving: true
      });

      try {
        const detail = await saveSceneHotspots(
          this.data.sceneId,
          (this.data.draftItems || []).map((item) => ({
            id: item.id,
            rect: item.rect
          }))
        );

        this.setupScene(Object.assign({}, detail, {
          sceneTabs: this.data.sceneTabs
        }));

        wx.showToast({
          title: '热点已保存',
          icon: 'success',
          duration: 1200
        });
      } catch (error) {
        this.setData({
          isSaving: false
        });
        wx.showToast({
          title: error.message || '热点保存失败',
          icon: 'none',
          duration: 1500
        });
      }
    },

    stopAudio() {
      if (this.audioContext) {
        this.audioContext.stop();
      }
    },

    destroyAudio() {
      if (this.audioContext) {
        this.audioContext.destroy();
        this.audioContext = null;
      }
      if (this.ttsAudioContext) {
        this.ttsAudioContext.stop();
        this.ttsAudioContext.destroy();
        this.ttsAudioContext = null;
      }
    }
  };
}

module.exports = {
  createScenePage
};
