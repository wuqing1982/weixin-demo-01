const sceneData = {
  sceneId: 'picnic',
  title: '野餐时光',
  background: '/assets/images/picnic.jpg',
  items: [
    {
      id: 'pizza',
      word: 'pizza',
      ipa: '/ˈpiːtsə/',
      meaning: '披萨',
      sentence: "Let's eat pizza together!",
      sentenceTranslation: '让我们一起吃披萨吧！',
      rect: { l: 40.0, t: 60.0, w: 20.0, h: 20.0 },
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_pizza_lets_eat_pizza_together.mp3'
    },
    {
      id: 'watermelon',
      word: 'watermelon',
      ipa: '/ˈwɔːtərˌmelən/',
      meaning: '西瓜',
      sentence: 'Watermelons are sweet and refreshing.',
      sentenceTranslation: '西瓜又甜又解渴。',
      rect: { l: 70.0, t: 50.0, w: 15.0, h: 15.0 },
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_watermelon_watermelons_are_sweet_and_refreshing.mp3'
    },
    {
      id: 'cake',
      word: 'cake',
      ipa: '/keɪk/',
      meaning: '蛋糕',
      sentence: 'The birthday cake is decorated with colorful candies.',
      sentenceTranslation: '生日蛋糕上装饰着五颜六色的糖果。',
      rect: { l: 30.0, t: 35.0, w: 12.0, h: 12.0 },
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_cake_the_birthday_cake_is_decorated_with.mp3'
    },
    {
      id: 'orange',
      word: 'orange',
      ipa: '/ˈɔːrɪndʒ/',
      meaning: '橙子',
      sentence: 'Oranges are a healthy snack.',
      sentenceTranslation: '橙子是一种健康的零食。',
      rect: { l: 80.0, t: 65.0, w: 10.0, h: 10.0 },
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_orange_oranges_are_a_healthy_snack.mp3'
    },
    {
      id: 'spoon',
      word: 'spoon',
      ipa: '/spuːn/',
      meaning: '勺子',
      sentence: 'Use the spoon to eat your food.',
      sentenceTranslation: '用勺子吃你的食物。',
      rect: { l: 85.0, t: 75.0, w: 5.0, h: 5.0 },
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_spoon_use_the_spoon_to_eat_your_food.mp3'
    }
  ],
  verbs: [
    {
      id: 'v1',
      word: 'eat',
      ipa: '/iːt/',
      meaning: '吃',
      sentence: "Let's eat pizza together!",
      sentenceTranslation: '让我们一起吃披萨吧！',
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_v1_lets_eat_pizza_together.mp3'
    },
    {
      id: 'v2',
      word: 'drink',
      ipa: '/drɪŋk/',
      meaning: '喝',
      sentence: 'Drink some watermelon juice!',
      sentenceTranslation: '喝一些西瓜汁吧！',
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_v2_drink_some_watermelon_juice.mp3'
    },
    {
      id: 'v3',
      word: 'serve',
      ipa: '/sɜːrv/',
      meaning: '盛放',
      sentence: 'Serve yourself an orange slice.',
      sentenceTranslation: '给自己盛一片橙子。',
      audio: '/assets/audio/picnic/picnic_en-US-JennyNeural_US_female_v3_serve_yourself_an_orange_slice.mp3'
    }
  ]
};

module.exports = sceneData;
