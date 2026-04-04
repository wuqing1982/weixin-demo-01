const sceneData = {
  sceneId: 'fruit_bowl',
  title: '水果拼盘',
  background: '/assets/images/fruit_bowl.jpg',
  items: [
    {
      id: 'strawberry',
      word: 'strawberry',
      ipa: '/ˈstrɔːˌberi/',
      meaning: '草莓',
      sentence: 'The strawberry is red and sweet.',
      sentenceTranslation: '这个草莓是红色的，很甜。',
      rect: { l: 50.0, t: 20.0, w: 25.0, h: 25.0 },
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_strawberry_the_strawberry_is_red_and_sweet.mp3'
    },
    {
      id: 'melon',
      word: 'melon',
      ipa: '/ˈmelən/',
      meaning: '蜜瓜',
      sentence: 'The melon is green and juicy.',
      sentenceTranslation: '这个蜜瓜是绿色的，很多汁。',
      rect: { l: 25.0, t: 40.0, w: 25.0, h: 25.0 },
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_melon_the_melon_is_green_and_juicy.mp3'
    },
    {
      id: 'pineapple',
      word: 'pineapple',
      ipa: '/ˈpaɪˌnæpəl/',
      meaning: '菠萝',
      sentence: 'The pineapple is yellow and tropical.',
      sentenceTranslation: '这个菠萝是黄色的，带有热带水果的感觉。',
      rect: { l: 75.0, t: 40.0, w: 25.0, h: 25.0 },
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_pineapple_the_pineapple_is_yellow_and_tropical.mp3'
    },
    {
      id: 'cantaloupe',
      word: 'cantaloupe',
      ipa: '/ˈkæn.təˌluːp/',
      meaning: '哈密瓜',
      sentence: 'The cantaloupe is orange and refreshing.',
      sentenceTranslation: '这个哈密瓜是橙色的，很清爽。',
      rect: { l: 25.0, t: 60.0, w: 25.0, h: 25.0 },
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_cantaloupe_the_cantaloupe_is_orange_and_refreshing.mp3'
    },
    {
      id: 'watermelon',
      word: 'watermelon',
      ipa: '/ˈwɔːtərˌmelən/',
      meaning: '西瓜',
      sentence: 'The watermelon is red and hydrating.',
      sentenceTranslation: '这个西瓜是红色的，很解渴。',
      rect: { l: 50.0, t: 60.0, w: 25.0, h: 25.0 },
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_watermelon_the_watermelon_is_red_and_hydrating.mp3'
    }
  ],
  verbs: [
    {
      id: 'v1',
      word: 'eat',
      ipa: '/iːt/',
      meaning: '吃',
      sentence: "Let's eat a strawberry!",
      sentenceTranslation: '让我们吃一颗草莓吧！',
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_eat_lets_eat_a_strawberry.mp3'
    },
    {
      id: 'v2',
      word: 'slice',
      ipa: '/sliːs/',
      meaning: '切片',
      sentence: 'Can you slice the melon for me?',
      sentenceTranslation: '你能帮我切一下蜜瓜吗？',
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_slice_can_you_slice_the_melon_for.mp3'
    },
    {
      id: 'v3',
      word: 'serve',
      ipa: '/sɜːrv/',
      meaning: '盛放',
      sentence: 'Please serve the pineapple on the plate.',
      sentenceTranslation: '请把菠萝盛放在盘子里。',
      audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_serve_please_serve_the_pineapple_on_the.mp3'
    }
  ]
};

module.exports = sceneData;
