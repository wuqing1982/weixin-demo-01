const sceneData = {
  sceneId: 'bedroom',
  title: '温馨卧室',
  background: '/assets/images/bedroom.png',
  items: [
    {id: 'bookshelf', word: 'bookshelf', ipa: '/bʊkˌʃelf/', meaning: '书架', sentence: 'Look at the bookshelf with many books.', sentenceTranslation: '看那个有很多书的书架。', rect: {l: 30.0, t: 40.0, w: 35.0, h: 50.0}, audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_bookshelf_look_at_the_bookshelf_with_many.mp3'},
    {id: 'teddy_bear', word: 'teddy bear', ipa: '/ˈtɛdi ˈbeər/', meaning: '泰迪熊', sentence: 'The teddy bear is hanging on the wall.', sentenceTranslation: '泰迪熊挂在墙上。', rect: {l: 60.0, t: 45.0, w: 20.0, h: 25.0}, audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_teddy_bear_the_teddy_bear_is_hanging_on.mp3'},
    {id: 'beanbag', word: 'beanbag', ipa: '/ˈbiːnˌbæg/', meaning: '豆袋椅', sentence: 'You can sit on the beanbag to read a book.', sentenceTranslation: '你可以坐在豆袋椅上看书。', rect: {l: 70.0, t: 80.0, w: 20.0, h: 20.0}, audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_beanbag_you_can_sit_on_the_beanbag.mp3'},
    {id: 'blanket', word: 'blanket', ipa: '/ˈblæŋkɪt/', meaning: '毯子', sentence: 'The blanket is on the bed.', sentenceTranslation: '毯子在床上。', rect: {l: 0.0, t: 70.0, w: 30.0, h: 30.0}, audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_blanket_the_blanket_is_on_the_bed.mp3'},
    {id: 'wall_lamp', word: 'wall lamp', ipa: '/ˈwɔːl læmp/', meaning: '壁灯', sentence: 'The wall lamp is turned on.', sentenceTranslation: '壁灯开着。', rect: {l: 30.0, t: 5.0, w: 10.0, h: 10.0}, audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_wall_lamp_the_wall_lamp_is_turned_on.mp3'}
  ],
  verbs: [
    {id: 'v1', word: 'look at', ipa: '/lʊk æt/', meaning: '看', sentence: 'Look at the bookshelf with many books.', sentenceTranslation: '看看书架上有很多书。', audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_v1_look_at_the_bookshelf_with_many.mp3'},
    {id: 'v2', word: 'hang', ipa: '/hæŋ/', meaning: '挂', sentence: 'Hang the teddy bear on the wall.', sentenceTranslation: '把泰迪熊挂在墙上。', audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_v2_hang_the_teddy_bear_on_the.mp3'},
    {id: 'v3', word: 'sit', ipa: '/sɪt/', meaning: '坐', sentence: 'Sit on the beanbag to read a book.', sentenceTranslation: '坐在豆袋椅上读一本书。', audio: '/assets/audio/bedroom/bedroom_en-US-JennyNeural_US_female_v3_sit_on_the_beanbag_to_read.mp3'}
  ],
};

module.exports = sceneData;
