<template>
  <div class="layout-container" :class="{ 'sidebar-collapsed': isSidebarCollapsed, 'mobile-menu-open': isMobileMenuOpen }">
    <div class="mobile-backdrop" @click="toggleMobileMenu"></div>
    <aside class="sidebar">
      <div class="logo-area">
        <div class="logo-icon">🏫</div>
        <div class="logo-text">LMS 图书馆</div>
      </div>
      <nav class="nav-menu">
        <div 
          v-for="item in menuItems" 
          :key="item.path"
          :class="['nav-item', { active: currentPath === item.path }]"
          @click="navigate(item.path)"
          :title="item.name"
        >
          <span class="icon">{{ item.icon }}</span>
          <span class="text">{{ item.name }}</span>
        </div>
      </nav>
      <div class="sidebar-toggle" @click="toggleSidebar" :title="isSidebarCollapsed ? '展开导航' : '收起导航'">
        <span class="chevron"></span>
      </div>
    </aside>

    <section class="main-wrapper">
      <header class="top-header">
        <div class="header-left">
          <button class="hamburger-btn" @click="toggleMobileMenu">☰</button>
          <div class="breadcrumb">
            <span class="current-page-icon">{{ currentPageIcon }}</span>
            <h2 class="page-title">{{ currentPageName }}</h2>
          </div>
        </div>
        <div class="user-profile">
          <span class="avatar">👤</span>
          <div class="user-info">
            <span class="username">{{ user.username || '访客' }}</span>
            <span class="role-badge" :class="user.role">{{ userRoleName }}</span>
          </div>
          <button class="logout-btn" @click="handleLogout" title="退出登录">🚪</button>
        </div>
      </header>

      <main class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </section>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

export default {
  name: 'WebLayout',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const user = ref({ username: '', role: 'student' })
    const isSidebarCollapsed = ref(false)
    const isMobileMenuOpen = ref(false)

    const baseMenuItems = [
      { name: '仪表盘', path: '/dashboard', icon: '📊' },
      { name: '图书查询', path: '/books', icon: '📚' },
      { name: '我的借阅', path: '/borrow', icon: '📖' },
      { name: '座位预约', path: '/seats', icon: '🪑' }
    ];

    const adminMenuItems = [
        { name: '管理座位', path: '/admin/seats', icon: '⚙️' },
        { name: '数据同步', path: '/admin/data-sync', icon: '🔄' },
        { name: '同步报表', path: '/admin/sync-stats', icon: '📈' },
        { name: '系统设置', path: '/admin/settings', icon: '🛠️' }
    ];

    const menuItems = ref([...baseMenuItems]);
    const allMenuItems = [...baseMenuItems, ...adminMenuItems];

    const currentPath = computed(() => route.path)
    
    const currentPage = computed(() => allMenuItems.find(i => i.path === route.path));
    const currentPageName = computed(() => currentPage.value ? currentPage.value.name : '系统页面')
    const currentPageIcon = computed(() => currentPage.value ? currentPage.value.icon : '📄')

    const userRoleName = computed(() => user.value.role === 'admin' ? '管理员' : '学生')

    const toggleSidebar = () => {
      isSidebarCollapsed.value = !isSidebarCollapsed.value;
    }
    const toggleMobileMenu = () => {
      isMobileMenuOpen.value = !isMobileMenuOpen.value;
    }

    watch(route, () => {
      // Close mobile menu on route change
      if (isMobileMenuOpen.value) {
        isMobileMenuOpen.value = false;
      }
    });

    onMounted(() => {
      const userStr = sessionStorage.getItem('user')
      if (userStr) {
        try {
          user.value = JSON.parse(userStr)
          if (user.value.role === 'admin' && menuItems.value.length === baseMenuItems.length) {
            menuItems.value.push(...adminMenuItems);
          }
        } catch (e) {
          console.error("Failed to parse user data, redirecting to login.", e);
          sessionStorage.removeItem('user');
          sessionStorage.removeItem('token');
          router.push('/login');
        }
      } else {
        router.push('/login')
      }
    })

    const navigate = (path) => {
      router.push(path)
    }

    const handleLogout = () => {
      if(confirm('确定要退出登录吗？👋')) {
        sessionStorage.removeItem('token')
        sessionStorage.removeItem('user')
        router.push('/login')
      }
    }

    return { 
      user, 
      menuItems, 
      currentPath, 
      currentPageName, 
      currentPageIcon, 
      userRoleName, 
      navigate, 
      handleLogout,
      isSidebarCollapsed,
      toggleSidebar,
      isMobileMenuOpen,
      toggleMobileMenu,
    }
  }
}
</script>

<style scoped>
/* Base Layout */
.layout-container {
  display: flex;
  height: 100vh;
  background-color: #f8f9fa;
  font-family: 'Segoe UI', system-ui, sans-serif;
  overflow-x: hidden;
}

/* Sidebar */
.sidebar {
  position: relative;
  width: 260px;
  background: white;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(0,0,0,0.05);
  z-index: 100;
  transition: width 0.3s ease-in-out;
  flex-shrink: 0;
}
.logo-area {
  height: 80px; display: flex; align-items: center; justify-content: center; gap: 12px;
  border-bottom: 1px solid #f0f0f0; flex-shrink: 0; overflow: hidden;
}
.logo-icon { font-size: 32px; transition: transform 0.3s ease; }
.logo-text { font-size: 20px; font-weight: 700; color: #333; letter-spacing: 1px; transition: opacity 0.2s ease, transform 0.3s ease; }
.nav-menu { padding: 20px 15px; flex: 1; overflow-y: auto; overflow-x: hidden; }
.nav-item {
  display: flex; align-items: center; padding: 14px 20px; margin-bottom: 8px; border-radius: 12px;
  cursor: pointer; color: #666; transition: all 0.3s ease; font-weight: 500; white-space: nowrap;
}
.nav-item .icon { margin-right: 12px; font-size: 18px; }
.nav-item:hover { background-color: #f3f4f6; color: #4f46e5; transform: translateX(5px); }
.nav-item.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; box-shadow: 0 4px 12px rgba(118, 75, 162, 0.3); }
.nav-item .text { transition: opacity 0.2s ease, transform 0.3s ease; }

/* Desktop Collapsed Sidebar */
.sidebar-collapsed .sidebar { width: 88px; }
.sidebar-collapsed .logo-text, .sidebar-collapsed .nav-item .text { opacity: 0; transform: translateX(-20px); width: 0; pointer-events: none; }
.sidebar-collapsed .logo-area, .sidebar-collapsed .nav-item { justify-content: center; padding: 14px; }
.sidebar-collapsed .nav-item .icon { margin-right: 0; }
.sidebar-collapsed .nav-item:hover { transform: translateX(0); }
.sidebar-collapsed .logo-icon { transform: rotate(360deg); }

/* Sidebar Toggle Button */
.sidebar-toggle {
  position: absolute;
  top: 90px;
  right: -15px; /* Overlap the main content area */
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 101;
}
.sidebar-toggle:hover {
  background-color: #764ba2;
  border-color: #764ba2;
}
.sidebar-toggle .chevron {
  border: solid #555;
  border-width: 0 2px 2px 0;
  display: inline-block;
  width: 7px;
  height: 7px;
  transform: rotate(135deg); /* Points left */
  transition: transform 0.3s ease-in-out;
}
.sidebar-toggle:hover .chevron {
  border-color: white;
}
.sidebar-collapsed .sidebar-toggle .chevron {
  transform: rotate(-45deg); /* Points right */
}


/* Hamburger Button for Mobile */
.hamburger-btn { display: none; background: none; border: none; font-size: 24px; cursor: pointer; color: #333; }

/* Main Area */
.main-wrapper { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.top-header {
  height: 80px; background: white; display: flex; align-items: center; justify-content: space-between;
  padding: 0 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.03);
  position: relative;
  z-index: 90;
}
.header-left { display: flex; align-items: center; gap: 15px; }
.breadcrumb { display: flex; align-items: center; gap: 10px; }
.current-page-icon { font-size: 24px; }
.page-title { margin: 0; font-size: 20px; color: #333; font-weight: 600; }

.user-profile { display: flex; align-items: center; gap: 15px; background: #f8f9fa; padding: 8px 16px; border-radius: 30px; }
.avatar { font-size: 20px; background: #fff; padding: 6px; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
.user-info { display: flex; flex-direction: column; line-height: 1.2; }
.username { font-size: 14px; font-weight: 600; color: #333; }
.role-badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; display: inline-block; width: fit-content; }
.role-badge.admin { background: #fee2e2; color: #ef4444; }
.role-badge.student { background: #e0e7ff; color: #4f46e5; }
.logout-btn { background: none; border: none; font-size: 20px; cursor: pointer; padding: 8px; border-radius: 50%; transition: background 0.2s; }
.logout-btn:hover { background: #fee2e2; }

.content-area { flex: 1; padding: 30px 40px; overflow-y: auto; }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Mobile Backdrop */
.mobile-backdrop { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 99; }
.mobile-menu-open .mobile-backdrop { display: block; }

/* ----- Responsive Media Queries ----- */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    transform: translateX(-100%);
    transition: transform 0.3s ease-in-out;
  }
  .mobile-menu-open .sidebar {
    transform: translateX(0);
  }
  .sidebar-toggle {
    display: none; /* Hide desktop toggle on mobile */
  }
  .hamburger-btn {
    display: block; /* Show hamburger on mobile */
  }
  .top-header {
    padding: 0 15px;
  }
  .content-area {
    padding: 15px;
  }
  .user-profile {
    gap: 8px;
    padding: 6px 10px;
  }
  .user-profile .user-info {
    display: none; /* Hide user info text on mobile */
  }
  .page-title {
    max-width: 150px; /* Adjust as needed */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 0;
  }
}
</style>