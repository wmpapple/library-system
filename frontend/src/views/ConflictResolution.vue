<template>
  <div class="conflict-resolution-container">
    <div v-if="!conflictDetails" class="verification-box">
      <div class="verification-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-shield-lock" viewBox="0 0 16 16">
          <path d="M5.338 1.59a61.44 61.44 0 0 0-2.837.856.481.481 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.725 10.725 0 0 0 2.287 2.233c.346.244.652.42.893.533.12.057.218.095.293.118a.55.55 0 0 0 .101.025.615.615 0 0 0 .1-.025c.076-.023.174-.06.294-.118.24-.113.547-.29.893-.533a10.726 10.726 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.952-.325-1.882-.626-2.837-.855C8.36 1.114 8.165 1.1 8 1.1c-.166 0-.36.014-.662.09zM8 11.823c-.634 0-1.167-.22-1.619-.657C5.935 10.726 5.5 9.86 5.5 8.658c0-1.2.435-2.066.881-2.508C6.833 5.71 7.366 5.5 8 5.5c.634 0 1.167.22 1.619.657.445.442.881 1.308.881 2.508 0 1.202-.435 2.066-.881 2.508-.452.437-.985.657-1.619.657z"/>
        </svg>
        <h2>Conflict Verification</h2>
      </div>
      <p v-if="adminEmail">
        Please enter the password for <strong>{{ adminEmail }}</strong> to view the conflict details.
      </p>
      <p v-else>
        A data conflict has been detected. Please enter your password to view the details.
      </p>
      <form @submit.prevent="verifyAccess">
        <div class="form-group">
          <label for="password">Password</label>
          <input type="password" id="password" v-model="password" required autocomplete="current-password">
        </div>
        <div v-if="error" class="error-message">{{ error }}</div>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Verifying...' : 'View Conflict' }}
        </button>
      </form>
    </div>

    <div v-if="conflictDetails" class="details-box">
      <h2>Conflict Details (ID: {{ conflictDetails.id }})</h2>
      <p>The following conflicting data was found. Please review the versions and choose the correct one in the admin panel.</p>
      
      <div class="conflict-data">
        <div v-for="(data, db_key) in conflictDetails.conflicting_data" :key="db_key" class="data-source">
          <h3>Source: <code>{{ db_key }}</code></h3>
          <div class="data-block">
            <div v-for="key in Object.keys(data)" :key="key" :class="{ 'conflict-field': conflictingFields.has(key) }">
              <strong>"{{ key }}"</strong>: <span>{{ JSON.stringify(data[key]) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <p class="resolution-note">
        To resolve this, please go to the 
        <router-link to="/admin/data-sync" target="_blank" rel="noopener noreferrer">Data Conflicts</router-link> 
        page in the admin dashboard and use the 'Resolve' function for conflict ID {{ conflictDetails.id }}.
      </p>
    </div>
  </div>
</template>

<script>
import api from '@/api';

export default {
  name: 'ConflictResolution',
  data() {
    return {
      password: '',
      token: null,
      adminEmail: null,
      loading: false,
      error: null,
      conflictDetails: null,
    };
  },
  computed: {
    conflictingFields() {
      if (!this.conflictDetails) return new Set();

      const allData = Object.values(this.conflictDetails.conflicting_data);
      if (allData.length < 2) return new Set();

      const conflictingKeys = new Set();
      const allKeys = new Set(allData.flatMap(data => Object.keys(data)));

      for (const key of allKeys) {
        const values = new Set(allData.map(data => JSON.stringify(data[key])));
        if (values.size > 1) {
          conflictingKeys.add(key);
        }
      }
      return conflictingKeys;
    }
  },
  created() {
    this.token = this.$route.params.token;
    if (!this.token) {
      this.error = "No verification token found. Please use the link from your email.";
      return;
    }
    this.decodeToken();
  },
  methods: {
    decodeToken() {
      try {
        const payloadBase64 = this.token.split('.')[1];
        const decodedPayload = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'));
        const payload = JSON.parse(decodedPayload);
        this.adminEmail = payload.sub;
      } catch (e) {
        console.error("Failed to decode JWT payload:", e);
        this.error = "Invalid verification token.";
      }
    },
    async verifyAccess() {
      if (!this.password) {
        this.error = "Password is required.";
        return;
      }
      this.loading = true;
      this.error = null;

      try {
        const response = await api.post('/conflicts/verify-access', {
          token: this.token,
          password: this.password,
        });
        this.conflictDetails = response.data;
      } catch (error) {
        if (error.response && error.response.data && error.response.data.detail) {
          this.error = error.response.data.detail;
        } else {
          this.error = "An unexpected error occurred. Please try again.";
        }
        console.error("Verification failed:", error);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.conflict-resolution-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 40px;
  min-height: 100vh;
  background-color: #f4f7f6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.verification-box, .details-box {
  width: 100%;
  max-width: 700px;
  background: #fff;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
}

.verification-box {
  text-align: center;
}

.verification-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
}

.verification-header .bi-shield-lock {
  color: #337ab7;
}

h2 {
  color: #333;
  margin: 0;
  font-weight: 600;
}

p {
  color: #555;
  margin-bottom: 25px;
  line-height: 1.6;
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

input[type="password"] {
  width: 100%;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 16px;
}

button {
  width: 100%;
  padding: 12px;
  background-color: #337ab7;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:disabled {
  background-color: #a9a9a9;
  cursor: not-allowed;
}

button:not(:disabled):hover {
  background-color: #286090;
}

.error-message {
  color: #d9534f;
  background-color: #f2dede;
  border: 1px solid #ebccd1;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.details-box {
  text-align: left;
}

.details-box h2 {
    color: #d9534f;
}

.conflict-data {
  margin-top: 20px;
}

.data-source {
  background-color: #fdfdfd;
  border: 1px solid #eee;
  border-radius: 5px;
  padding: 20px;
  margin-bottom: 20px;
}

.data-source h3 {
  margin-top: 0;
  color: #333;
  font-size: 1.2em;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

code {
  background-color: #e3f2fd;
  padding: 3px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

.data-block {
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 15px;
  border-radius: 5px;
  font-size: 14px;
  font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
}

.data-block > div {
  padding: 2px 0;
}

.conflict-field {
  color: #ff7b72;
  font-weight: bold;
}

.conflict-field > span {
  background-color: rgba(255, 123, 114, 0.2);
  padding: 2px 4px;
  border-radius: 3px;
}

.resolution-note {
  margin-top: 30px;
  padding: 15px;
  background-color: #eef7ff;
  border: 1px solid #bce8f1;
  border-radius: 4px;
  color: #31708f;
  text-align: center;
}
</style>