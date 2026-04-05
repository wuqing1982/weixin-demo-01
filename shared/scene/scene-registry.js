const SCENES = [
  {
    sceneId: 'scene_breakfast',
    title: '\u8425\u517b\u65e9\u9910',
    route: '/pages/scene_runtime/index?sceneId=scene_breakfast'
  },
  {
    sceneId: 'scene_zoo',
    title: '\u52a8\u7269\u56ed',
    route: '/pages/scene_runtime/index?sceneId=scene_zoo'
  }
];

function getSceneNeighbors(sceneId) {
  const index = SCENES.findIndex((item) => item.sceneId === sceneId);
  if (index === -1) {
    return {
      prevScene: null,
      nextScene: null,
      sceneTabs: SCENES
    };
  }

  return {
    prevScene: SCENES[index - 1] || null,
    nextScene: SCENES[index + 1] || null,
    sceneTabs: SCENES
  };
}

module.exports = {
  SCENES,
  getSceneNeighbors
};
