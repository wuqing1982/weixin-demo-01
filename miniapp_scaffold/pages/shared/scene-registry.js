const SCENES = [
  {
    sceneId: 'scene_breakfast',
    title: '营养早餐'
  },
  {
    sceneId: 'scene_zoo',
    title: '动物园'
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
