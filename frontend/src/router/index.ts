import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/test',
            name: 'Test',
            component: () => import('@/views/Test.vue')
        },
        {
            path: '/login',
            name: 'Login',
            component: () => import('@/views/Login.vue')
        },
        {
            path: '/',
            component: () => import('@/layouts/MainLayout.vue'),
            meta: { requiresAuth: true },
            children: [
                {
                    path: '',
                    name: 'Dashboard',
                    component: () => import('@/views/Dashboard.vue')
                },
                {
                    path: 'projects',
                    name: 'Projects',
                    component: () => import('@/views/Projects.vue')
                },
                {
                    path: 'modules',
                    name: 'Modules',
                    component: () => import('@/views/Modules.vue')
                },
                {
                    path: 'pages',
                    name: 'Pages',
                    component: () => import('@/views/Pages.vue')
                },
                {
                    path: 'cases',
                    name: 'TestCases',
                    component: () => import('@/views/TestCases.vue')
                },
                {
                    path: 'recording',
                    name: 'Recording',
                    component: () => import('@/views/Recording.vue')
                },
                {
                    path: 'suites',
                    name: 'TestSuites',
                    component: () => import('@/views/TestSuites.vue')
                },
                {
                    path: 'elements',
                    name: 'PageElements',
                    component: () => import('@/views/PageElements.vue')
                },
                {
                    path: 'reports',
                    name: 'Reports',
                    component: () => import('@/views/Reports.vue')
                }
            ]
        }
    ]
})

router.beforeEach(async (to, _from, next) => {
    const userStore = useUserStore()

    if (to.meta.requiresAuth && !userStore.token) {
        next('/login')
    } else if (userStore.token && !userStore.user) {
        await userStore.fetchUser()
        next()
    } else {
        next()
    }
})

export default router
