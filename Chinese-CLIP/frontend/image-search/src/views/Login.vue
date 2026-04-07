<template>
  <div class="taobao-login-container">
    <div class="login-header">
      <div class="logo">

        <span class="logo-text">Chinese-CLIP商品检索系统</span>
      </div>
    </div>

    <div class="login-main">


      <div class="login-form-container">
        <div class="login-tabs">
          <div
            class="tab"
            :class="{ active: activeTab === 'login' }"
            @click="activeTab = 'login'"
          >
            账户密码登录
          </div>
          <div
            class="tab"
            :class="{ active: activeTab === 'register' }"
            @click="activeTab = 'register'"
          >
            注册账号
          </div>
        </div>

        <!-- 登录表单 -->
        <div class="login-form" v-if="activeTab === 'login'">
          <div v-if="errorMessage" class="error-message">
            <i class="error-icon">!</i>
            {{ errorMessage }}
          </div>

          <form @submit.prevent="login">
            <div class="input-group">
              <div class="input-icon">👤</div>
              <input
                type="text"
                v-model="username"
                placeholder="会员名/邮箱/手机号"
                autocomplete="username"
                required
              />
            </div>

            <div class="input-group">
              <div class="input-icon">🔒</div>
              <input
                type="password"
                v-model="password"
                placeholder="请输入登录密码"
                autocomplete="current-password"
                required
              />
            </div>

            <div class="login-options">
              <label class="remember-me">
                <input type="checkbox" v-model="rememberMe" />
                <span>记住我</span>
              </label>
              <a href="#" class="forgot-password">忘记密码</a>
            </div>

            <button
              type="submit"
              class="login-btn"
              :disabled="isLoading"
            >
              {{ isLoading ? '登录中...' : '登 录' }}
            </button>
          </form>

          <div class="login-links">
            <a href="#" @click.prevent="activeTab = 'register'">免费注册</a>
            <span class="separator">|</span>
            <a href="#">密码登录</a>
            <span class="separator">|</span>
            <a href="#">验证码登录</a>
          </div>

          <div class="third-party-login">
            <div class="title">
              <span class="line"></span>
              <span class="text">其他账号登录</span>
              <span class="line"></span>
            </div>
            <div class="icons">
              <a href="#" class="icon-item" title="微信登录">
                <span class="social-icon">微</span>
              </a>
              <a href="#" class="icon-item" title="支付宝登录">
                <span class="social-icon">支</span>
              </a>
            </div>
          </div>
        </div>

        <!-- 注册表单 -->
        <div class="login-form" v-if="activeTab === 'register'">
          <div v-if="errorMessage" class="error-message">
            <i class="error-icon">!</i>
            {{ errorMessage }}
          </div>

          <div v-if="successMessage" class="success-message">
            <i class="success-icon">✓</i>
            {{ successMessage }}
          </div>

          <form @submit.prevent="register">
            <div class="input-group">
              <div class="input-icon">👤</div>
              <input
                type="text"
                v-model="registerForm.username"
                placeholder="请设置用户名"
                required
              />
            </div>

            <div class="input-group">
              <div class="input-icon">📧</div>
              <input
                type="email"
                v-model="registerForm.email"
                placeholder="请输入邮箱（选填）"
              />
            </div>

            <div class="input-group">
              <div class="input-icon">🔒</div>
              <input
                type="password"
                v-model="registerForm.password"
                placeholder="请设置登录密码"
                required
              />
            </div>

            <div class="input-group">
              <div class="input-icon">🔒</div>
              <input
                type="password"
                v-model="registerForm.confirmPassword"
                placeholder="请确认登录密码"
                required
              />
            </div>

            <div class="login-options">
              <label class="remember-me">
                <input type="checkbox" v-model="registerForm.agreement" required />
                <span>我已阅读并同意 <a href="#" class="agreement-link">服务条款</a></span>
              </label>
            </div>

            <button
              type="submit"
              class="login-btn"
              :disabled="isLoading || !isFormValid"
            >
              {{ isLoading ? '注册中...' : '注 册' }}
            </button>
          </form>

          <div class="login-links">
            <a href="#" @click.prevent="activeTab = 'login'">返回登录</a>
          </div>
        </div>
      </div>
    </div>

    <div class="login-footer">
      <p>© 2025 Chinese-CLIP商品检索系统 版权所有</p>
      <p class="current-time">当前时间: {{ currentTime }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'TaobaoLogin',
  data() {
    return {
      // 登录表单数据
      username: '',
      password: '',
      rememberMe: false,

      // 注册表单数据
      registerForm: {
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        agreement: false
      },

      // 共享状态
      activeTab: 'login',
      errorMessage: '',
      successMessage: '',
      isLoading: false,
      currentTime: '',
      timer: null
    };
  },
  computed: {
    isFormValid() {
      const { username, password, confirmPassword, agreement } = this.registerForm;
      return (
        username.length >= 3 &&
        password.length >= 6 &&
        password === confirmPassword &&
        agreement
      );
    }
  },
  methods: {
    // 更新当前时间
    updateCurrentTime() {
      const now = new Date();

      // 格式化为 YYYY-MM-DD HH:MM:SS
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');

      this.currentTime = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    },

    // 登录方法
    async login() {
      this.isLoading = true;
      this.errorMessage = '';

      try {
        // 使用后端服务器的完整URL
        const response = await axios.post('http://localhost:5000/auth/login', {
          username: this.username,
          password: this.password,
          remember: this.rememberMe
        }, {
          withCredentials: true  // 确保跨域请求携带凭证（cookies）
        });

        const data = response.data;

        if (data.status === 'success') {
          console.log('登录成功:', data);

          // 存储用户信息
          localStorage.setItem('user', JSON.stringify(data.user));

          // 重要：使用后端返回的重定向地址跳转
          this.$router.push(data.redirect || '/ImageSearch');

          // 显示成功消息
          this.$nextTick(() => {
            this.$emit('login-success', data.user);
          });
        } else {
          this.errorMessage = data.message || '登录失败，请重试';
        }
      } catch (error) {
        console.error('登录请求失败:', error);
        // 显示详细错误信息
        if (error.response) {
          // 服务器返回的错误响应
          this.errorMessage = error.response.data.message || `服务器错误: ${error.response.status}`;
        } else if (error.request) {
          // 请求发送但没有收到响应
          this.errorMessage = '无法连接到服务器，请检查网络连接';
        } else {
          // 请求设置触发的错误
          this.errorMessage = `请求错误: ${error.message}`;
        }
      } finally {
        this.isLoading = false;
      }
    },

    // 注册方法
    async register() {
      // 验证表单
      if (!this.isFormValid) {
        if (this.registerForm.password !== this.registerForm.confirmPassword) {
          this.errorMessage = '两次输入的密码不一致';
        } else if (this.registerForm.password.length < 6) {
          this.errorMessage = '密码长度至少为6位';
        } else if (this.registerForm.username.length < 3) {
          this.errorMessage = '用户名长度至少为3位';
        } else if (!this.registerForm.agreement) {
          this.errorMessage = '请同意服务条款';
        }
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';
      this.successMessage = '';

      try {
        // 调用后端注册API
        const response = await axios.post('http://localhost:5000/auth/register', {
          username: this.registerForm.username,
          email: this.registerForm.email || null, // 如果为空字符串，则发送null
          password: this.registerForm.password
        });

        const data = response.data;

        if (data.status === 'success') {
          console.log('注册成功:', data);

          // 显示成功消息
          this.successMessage = '注册成功！正在为您跳转...';

          // 存储用户信息
          localStorage.setItem('user', JSON.stringify(data.user));

          // 延迟2秒后跳转
          setTimeout(() => {
            this.$router.push(data.redirect || '/ImageSearch');
          }, 2000);

        } else {
          this.errorMessage = data.message || '注册失败，请重试';
        }
      } catch (error) {
        console.error('注册请求失败:', error);
        // 显示详细错误信息
        if (error.response) {
          // 服务器返回的错误响应
          this.errorMessage = error.response.data.message || `服务器错误: ${error.response.status}`;
        } else if (error.request) {
          // 请求发送但没有收到响应
          this.errorMessage = '无法连接到服务器，请检查网络连接';
        } else {
          // 请求设置触发的错误
          this.errorMessage = `请求错误: ${error.message}`;
        }
      } finally {
        this.isLoading = false;
      }
    },

    // 切换到注册页
    switchToRegister() {
      this.activeTab = 'register';
      this.errorMessage = '';
      this.successMessage = '';
    },

    // 切换到登录页
    switchToLogin() {
      this.activeTab = 'login';
      this.errorMessage = '';
      this.successMessage = '';
    }
  },
  // 如果用户已登录，直接跳转
  created() {
    // 组件创建时初始化时间
    this.updateCurrentTime();

    // 设置定时器，每秒更新一次时间
    this.timer = setInterval(this.updateCurrentTime, 1000);

    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const user = JSON.parse(storedUser);
        // 验证用户信息是否有效
        if (user && user.id) {
          // 已登录，跳转到ImageSearch页面
          this.$router.push('/ImageSearch');
        }
      } catch (e) {
        // JSON解析错误，清除无效数据
        localStorage.removeItem('user');
      }
    }
  },
  // 组件销毁前清除定时器
  beforeDestroy() {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }
};
</script>

<style scoped>
.taobao-login-container {
  font-family: 'PingFang SC', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background-color: #f5f5f5;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  color: #333;
}

.login-header {
  background-color: white;
  height: 80px;
  display: flex;
  align-items: center;
  padding: 0 50px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.logo {
  display: flex;
  align-items: center;
}

.logo-icon {
  width: 32px;
  height: 32px;
  margin-right: 10px;
}

.logo-text {
  font-size: 24px;
  color: #ff6700;
  font-weight: bold;
}

.login-main {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

.login-banner {
  width: 400px;
  height: 400px;
  margin-right: 50px;
  border-radius: 4px;
  overflow: hidden;
}

.login-banner img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.login-form-container {
  width: 350px;
  background-color: white;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.login-tabs {
  display: flex;
  height: 50px;
  border-bottom: 1px solid #f0f0f0;
}

.tab {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  transition: all 0.3s;
}

.tab.active {
  color: #ff6700;
  border-bottom: 2px solid #ff6700;
  font-weight: bold;
}

.login-form {
  padding: 25px;
}

.error-message {
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  padding: 8px 12px;
  border-radius: 4px;
  color: #ff4d4f;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.error-icon {
  display: inline-block;
  width: 18px;
  height: 18px;
  line-height: 16px;
  text-align: center;
  border-radius: 50%;
  background-color: #ff4d4f;
  color: white;
  margin-right: 8px;
  font-weight: bold;
}

.success-message {
  background-color: #f6ffed;
  border: 1px solid #b7eb8f;
  padding: 8px 12px;
  border-radius: 4px;
  color: #52c41a;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.success-icon {
  display: inline-block;
  width: 18px;
  height: 18px;
  line-height: 16px;
  text-align: center;
  border-radius: 50%;
  background-color: #52c41a;
  color: white;
  margin-right: 8px;
  font-weight: bold;
}

.input-group {
  position: relative;
  margin-bottom: 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
  height: 40px;
  display: flex;
  overflow: hidden;
}

.input-group:hover, .input-group:focus-within {
  border-color: #ff6700;
}

.input-icon {
  width: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f5f5;
  color: #999;
  border-right: 1px solid #ddd;
}

.input-group input {
  flex: 1;
  height: 100%;
  border: none;
  outline: none;
  padding: 0 12px;
  font-size: 14px;
}

.login-options {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  align-items: center;
}

.remember-me {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: #666;
}

.remember-me input {
  margin-right: 8px;
}

.forgot-password {
  font-size: 14px;
  color: #1890ff;
  text-decoration: none;
}

.login-btn {
  width: 100%;
  height: 40px;
  background-color: #ff6700;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.login-btn:hover {
  background-color: #ff4d00;
}

.login-btn:disabled {
  background-color: #ffa176;
  cursor: not-allowed;
}

.login-links {
  margin-top: 15px;
  text-align: center;
  font-size: 14px;
}

.login-links a {
  color: #666;
  text-decoration: none;
}

.login-links a:hover {
  color: #ff6700;
}

.separator {
  margin: 0 8px;
  color: #ddd;
}

.third-party-login {
  margin-top: 20px;
}

.third-party-login .title {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.line {
  flex: 1;
  height: 1px;
  background-color: #f0f0f0;
}

.text {
  padding: 0 12px;
  font-size: 12px;
  color: #999;
}

.icons {
  display: flex;
  justify-content: center;
}

.icon-item {
  width: 40px;
  height: 40px;
  margin: 0 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  text-decoration: none;
}

.social-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: #f5f5f5;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  color: #666;
}

.login-footer {
  text-align: center;
  padding: 20px 0;
  color: #999;
  font-size: 12px;
  margin-top: auto;
}

.login-footer p {
  margin: 5px 0;
}

.current-time {
  font-family: monospace;
  background-color: rgba(255, 103, 0, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.agreement-link {
  color: #1890ff;
  text-decoration: none;
}

.agreement-link:hover {
  color: #40a9ff;
  text-decoration: underline;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-banner {
    display: none;
  }

  .login-form-container {
    width: 90%;
    max-width: 350px;
  }

  .login-header {
    padding: 0 20px;
  }
}
</style>
