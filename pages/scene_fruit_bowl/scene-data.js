const sceneData = {
  sceneId: 'fruit_bowl',
  title: 'fruit_bowl',
  background: '/assets/images/fruit_bowl.png',
  items: [
    {id: 'strawberry', word: 'strawberry', ipa: '/ˈstrɔːbrɪdi/', meaning: '草莓', sentence: 'The strawberry is red and sweet.', sentenceTranslation: '这个草莓是红色的，很甜。', rect: {l: 50.0, t: 20.0, w: 25.0, h: 25.0}, audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_strawberry_the_strawberry_is_red_and_sweet.mp3'},
    {id: 'melon', word: 'melon', ipa: '/ˈmɛlən/', meaning: '哈密瓜', sentence: 'The melon is green and juicy.', sentenceTranslation: '这个哈密瓜是绿色的，多汁。', rect: {l: 25.0, t: 40.0, w: 25.0, h: 25.0}, audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_slice_can_you_slice_the_melon_for.mp3'},
    {id: 'pineapple', word: 'pineapple', ipa: '/pɪˈneɪpəl/', meaning: '菠萝', sentence: 'The pineapple is yellow and tropical.', sentenceTranslation: '这个菠萝是黄色的，热带水果。', rect: {l: 75.0, t: 40.0, w: 25.0, h: 25.0}, audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_pineapple_the_pineapple_is_yellow_and_tropical.mp3'},
    {id: 'cantaloupe', word: 'cantaloupe', ipa: '/kænˈtæloup/', meaning: '香瓜', sentence: 'The cantaloupe is orange and refreshing.', sentenceTranslation: '这个香瓜是橙色的，清爽可口。', rect: {l: 25.0, t: 60.0, w: 25.0, h: 25.0}, audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_cantaloupe_the_cantaloupe_is_orange_and_refreshing.mp3'},
    {id: 'watermelon', word: 'watermelon', ipa: '/ˈwɔːtərˌmɛlən/', meaning: '西瓜', sentence: 'The watermelon is red and hydrating.', sentenceTranslation: '这个西瓜是红色的，解渴。', rect: {l: 50.0, t: 60.0, w: 25.0, h: 25.0}, audio: '/assets/audio/fruit_bowl/fruit_bowl_en-US-JennyNeural_US_female_watermelon_the_watermelon_is_red_and_hydrating.mp3'}
  ],
  verbs: [
    {id: 'v1', word: 'eat', ipa: '/iːt/', meaning: '吃', sentence: 'Let's eat a strawberry!', sentenceTranslation: '让我们吃一颗草莓吧！', audio: ''},
    {id: 'v2', word: 'slice', ipa: '/sliːs/', meaning: '切片', sentence: 'Can you slice the melon for me?', sentenceTranslation: '你能帮我切一下哈密瓜吗？', audio: ''},
    {id: 'v3', word: 'serve', ipa: '/sɜːrv/', meaning: '盛放', sentence: 'Please serve the pineapple on the plate.', sentenceTranslation: '请把菠萝盛放在盘子里。', audio: ''}
  ],
};

module.exports = sceneData;
