// 文件路径: `Chinese-CLIP/frontend/image-search/src/router/index.js`
import { createRouter, createWebHistory } from 'vue-router'
import ImageSearch from '../views/ImageSearch.vue'
import Login from '../views/Login.vue'
import Favorites from '../views/Favorites.vue'
import Recommend from '../views/Recommend.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Login',
      component: Login
    },

    {
      path: '/ImageSearch',
      name: 'ImageSearch',
      component: ImageSearch
    },
    {
    path: '/favorites',
    name: 'Favorites',
    component: Favorites
  },
  {
    path: '/recommend',
    name: 'Recommend',
    component: Recommend
  }
  ]
})


export default router
