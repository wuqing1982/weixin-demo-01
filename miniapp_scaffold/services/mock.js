const MOCK_SCENES = [
  {
    sceneId: 'scene_breakfast',
    title: '营养早餐',
    coverUrl: 'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?auto=format&fit=crop&w=900&q=80',
    category: 'food',
    visibility: 'member',
    sceneType: 'public'
  },
  {
    sceneId: 'scene_zoo',
    title: '动物园',
    coverUrl: 'https://images.unsplash.com/photo-1546182990-dffeafbe841d?auto=format&fit=crop&w=900&q=80',
    category: 'animals',
    visibility: 'member',
    sceneType: 'public'
  }
];

const MOCK_SCENE_DETAIL = {
  sceneId: 'scene_breakfast',
  title: '营养早餐',
  background: 'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?auto=format&fit=crop&w=1200&q=80',
  cover: 'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?auto=format&fit=crop&w=900&q=80',
  items: [
    {
      id: 'porridge',
      word: 'porridge',
      ipa: '/ˈpɒrɪdʒ/',
      meaning: '粥',
      sentence: 'I eat porridge for breakfast.',
      sentenceTranslation: '我早餐吃粥。',
      rect: { l: 14, t: 23, w: 48, h: 16 },
      audio: ''
    },
    {
      id: 'egg',
      word: 'egg',
      ipa: '/eɡ/',
      meaning: '鸡蛋',
      sentence: 'The egg is on the plate.',
      sentenceTranslation: '鸡蛋在盘子里。',
      rect: { l: 58, t: 44, w: 18, h: 18 },
      audio: ''
    }
  ],
  verbs: [
    {
      id: 'v1',
      word: 'eat',
      ipa: '/iːt/',
      meaning: '吃',
      sentence: 'I eat porridge for breakfast.',
      sentenceTranslation: '我早餐吃粥。',
      audio: ''
    },
    {
      id: 'v2',
      word: 'cook',
      ipa: '/kʊk/',
      meaning: '煮',
      sentence: 'We cook breakfast together.',
      sentenceTranslation: '我们一起做早餐。',
      audio: ''
    }
  ],
  meta: {
    sceneType: 'public',
    ownerUserId: null,
    visibility: 'member',
    version: 1,
    category: 'food',
    tags: ['breakfast', 'food']
  }
};

module.exports = {
  MOCK_SCENES,
  MOCK_SCENE_DETAIL
};
