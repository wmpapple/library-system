import { createRouter, createWebHistory } from 'vue-router'
import Login from '../components/Login.vue'
import WebLayout from '../components/WebLayout.vue'
import Dashboard from '../views/Dashboard.vue'
import BookList from '../views/BookList.vue'
import MyBorrow from '../views/MyBorrow.vue'
import SeatReservation from '../views/SeatReservation.vue'
import AdminSeats from '../views/AdminSeats.vue'
import DataSynchronization from '../views/SyncLogs.vue'
import SyncStats from '../views/SyncStats.vue'

const routes = [
  { path: '/login', component: Login },
  {
    path: '/',
    component: WebLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: Dashboard },
      { path: 'books', component: BookList },
      { path: 'borrow', component: MyBorrow },
      { path: 'seats', component: SeatReservation },
      { path: 'admin/seats', component: AdminSeats, meta: { requiresAdmin: true } },
      { path: 'admin/data-sync', component: DataSynchronization, meta: { requiresAdmin: true } },
      { path: 'admin/sync-stats', name: 'SyncStats', component: SyncStats, meta: { requiresAdmin: true } },
      { path: 'admin/settings', component: () => import('../views/SystemSettings.vue'), meta: { requiresAdmin: true } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStr = sessionStorage.getItem('user');
  let isAdmin = false;
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      isAdmin = user && user.role === 'admin';
    } catch (e) {
      console.error("Failed to parse user data from sessionStorage", e);
    }
  }

  if (to.matched.some(record => record.meta.requiresAdmin) && !isAdmin) {
    // User is not an admin, but the route requires admin privileges.
    // Redirect them to a safe page.
    next('/dashboard');
  } else {
    // Proceed with navigation.
    next();
  }
});

export default router
