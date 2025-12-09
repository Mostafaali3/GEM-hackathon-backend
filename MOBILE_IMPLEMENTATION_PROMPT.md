# 📱 Mobile App Implementation Prompt (Kotlin/Android)

## Context
You are developing an Android app for the Grand Egyptian Museum using Kotlin. The backend API is running at `http://YOUR_SERVER_IP:8000`. You need to implement a Hybrid NFC Access System that allows users to authenticate at museum gates using their phone's Host Card Emulation (HCE).

---

## Requirements

### 1. **Virtual NFC ID Management**

Implement a persistent Virtual NFC ID system:

- **On first app launch or after user login**, generate a unique `virtual_nfc_id` using one of these formats:
  - UUID-based: `"GEM_${userId}_${UUID.randomUUID()}"`
  - Sequential: `"GEM_USER_${userId}"`
  - Pure UUID: `UUID.randomUUID().toString()`

- **Store the ID permanently** in SharedPreferences or EncryptedSharedPreferences:
  ```kotlin
  val PREF_VIRTUAL_NFC_ID = "virtual_nfc_id"
  ```

- **Check if ID exists** on every app launch:
  - If exists → Use the stored ID (no API call needed)
  - If null → Generate new ID and register with backend

- **Register the ID** with the backend via `POST /api/nfc/register`:
  ```json
  {
    "user_id": 123,
    "virtual_nfc_id": "GEM_USER_12345_abc-def-ghi"
  }
  ```

---

### 2. **Backend API Integration**

Create a Retrofit service with these endpoints:

#### **Base URL**
```kotlin
const val BASE_URL = "http://YOUR_SERVER_IP:8000/"
```

#### **Data Classes**
```kotlin
// PRIMARY LOGIN/REGISTER ENDPOINT (Use this!)
data class LoginRegisterRequest(
    val email: String,
    val name: String?,
    val gender: String?,
    val virtual_nfc_id: String
)

data class LoginRegisterResponse(
    val status: String,
    val message: String,
    val user: Visitor,
    val is_new_user: Boolean
)

// Legacy NFC registration (use login-register instead)
data class RegisterNFCRequest(
    val user_id: Int,
    val virtual_nfc_id: String
)

data class RegisterNFCResponse(
    val status: String,
    val message: String,
    val user_id: Int,
    val virtual_nfc_id: String
)

data class LinkCardRequest(
    val user_id: Int,
    val card_uid: String
)

data class LinkCardResponse(
    val status: String,
    val message: String,
    val user_id: Int,
    val card_uid: String
)

data class GateScanRequest(
    val scanned_id: String
)

data class GateScanResponse(
    val status: String,
    val user_name: String?,
    val welcome_message: String?
)

data class CreateVisitorRequest(
    val email: String,
    val name: String?,
    val gender: String?
)

data class Visitor(
    val id: Int,
    val email: String,
    val name: String?,
    val gender: String?,
    val joined_at: String,
    val virtual_nfc_id: String?,
    val physical_card_id: String?
)
```

#### **API Service Interface**
```kotlin
interface GemApiService {
    
    // PRIMARY ENDPOINT - Use this for login/register!
    @POST("api/auth/login-register")
    suspend fun loginOrRegister(
        @Body request: LoginRegisterRequest
    ): Response<LoginRegisterResponse>
    
    // Legacy endpoints (optional)
    @POST("api/nfc/register")
    suspend fun registerVirtualNFC(
        @Body request: RegisterNFCRequest
    ): Response<RegisterNFCResponse>
    
    @POST("api/cards/link")
    suspend fun linkPhysicalCard(
        @Body request: LinkCardRequest
    ): Response<LinkCardResponse>
    
    @POST("api/gate/scan")
    suspend fun scanAtGate(
        @Body request: GateScanRequest
    ): Response<GateScanResponse>
    
    @POST("visitors/")
    suspend fun createVisitor(
        @Body request: CreateVisitorRequest
    ): Response<Visitor>
    
    @GET("visitors/")
    suspend fun getAllVisitors(): Response<List<Visitor>>
}
```

**IMPORTANT**: Use `POST /api/auth/login-register` as your primary authentication endpoint. It handles both new user creation and existing user login in a single call, and automatically registers the NFC ID.

---

### 3. **NFC Manager Implementation**

Create a `NFCManager` class to handle Virtual NFC ID lifecycle:

```kotlin
class NFCManager(private val context: Context) {
    
    private val sharedPrefs = context.getSharedPreferences("gem_nfc_prefs", Context.MODE_PRIVATE)
    private val apiService = RetrofitClient.gemApiService
    
    companion object {
        private const val KEY_VIRTUAL_NFC_ID = "virtual_nfc_id"
        private const val KEY_IS_REGISTERED = "is_registered"
    }
    
    /**
     * Get or generate Virtual NFC ID
     * Returns existing ID if available, generates new one if not
     */
    fun getOrCreateVirtualNfcId(userId: Int): String {
        var virtualNfcId = sharedPrefs.getString(KEY_VIRTUAL_NFC_ID, null)
        
        if (virtualNfcId == null) {
            // Generate new ID (choose your format)
            virtualNfcId = "GEM_USER_${userId}_${UUID.randomUUID()}"
            
            // Store permanently
            sharedPrefs.edit()
                .putString(KEY_VIRTUAL_NFC_ID, virtualNfcId)
                .apply()
        }
        
        return virtualNfcId
    }
    
    /**
     * Login or register user with NFC ID in one call
     * This is the PRIMARY method to use
     */
    suspend fun loginOrRegister(
        email: String,
        name: String?,
        virtualNfcId: String
    ): Result<LoginRegisterResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val request = LoginRegisterRequest(
                    email = email,
                    name = name,
                    gender = null,
                    virtual_nfc_id = virtualNfcId
                )
                
                val response = apiService.loginOrRegister(request)
                
                if (response.isSuccessful && response.body() != null) {
                    val result = response.body()!!
                    
                    // Store the virtual NFC ID
                    sharedPrefs.edit()
                        .putString(KEY_VIRTUAL_NFC_ID, virtualNfcId)
                        .putBoolean(KEY_IS_REGISTERED, true)
                        .apply()
                    
                    Result.success(result)
                } else {
                    Result.failure(Exception("Login/Register failed: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
    
    /**
     * Register Virtual NFC ID with backend (LEGACY - use loginOrRegister instead)
     * Call this after user login
     */
    suspend fun registerWithBackend(userId: Int): Result<RegisterNFCResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val virtualNfcId = getOrCreateVirtualNfcId(userId)
                
                val request = RegisterNFCRequest(
                    user_id = userId,
                    virtual_nfc_id = virtualNfcId
                )
                
                val response = apiService.registerVirtualNFC(request)
                
                if (response.isSuccessful && response.body() != null) {
                    // Mark as registered
                    sharedPrefs.edit()
                        .putBoolean(KEY_IS_REGISTERED, true)
                        .apply()
                    
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Registration failed: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
     * Check if already registered
     */
    fun isRegistered(): Boolean {
        return sharedPrefs.getBoolean(KEY_IS_REGISTERED, false)
    }
    
    /**
     * Get stored Virtual NFC ID (returns null if not generated yet)
     */
    fun getVirtualNfcId(): String? {
        return sharedPrefs.getString(KEY_VIRTUAL_NFC_ID, null)
    }
    
    /**
     * Clear NFC data (for testing or logout)
     */
    fun clearNfcData() {
        sharedPrefs.edit().clear().apply()
    }
}
```

---

### 4. **HCE Service Implementation**

Implement Android's Host Card Emulation to broadcast your Virtual NFC ID:

#### **AndroidManifest.xml**
```xml
<uses-permission android:name="android.permission.NFC" />
<uses-feature android:name="android.hardware.nfc.hce" android:required="true" />

<application>
    <!-- Your HCE Service -->
    <service
        android:name=".nfc.GemHceService"
        android:exported="true"
        android:permission="android.permission.BIND_NFC_SERVICE">
        <intent-filter>
            <action android:name="android.nfc.cardemulation.action.HOST_APDU_SERVICE" />
        </intent-filter>
        
        <meta-data
            android:name="android.nfc.cardemulation.host_apdu_service"
            android:resource="@xml/apduservice" />
    </service>
</application>
```

#### **res/xml/apduservice.xml**
```xml
<host-apdu-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:description="@string/service_description"
    android:requireDeviceUnlock="false">
    <aid-group android:description="@string/aid_description" android:category="other">
        <!-- Your Application ID (AID) -->
        <aid-filter android:name="F0010203040506" />
    </aid-group>
</host-apdu-service>
```

#### **GemHceService.kt**
```kotlin
class GemHceService : HostApduService() {
    
    private lateinit var nfcManager: NFCManager
    
    override fun onCreate() {
        super.onCreate()
        nfcManager = NFCManager(this)
    }
    
    override fun processCommandApdu(commandApdu: ByteArray?, extras: Bundle?): ByteArray {
        // Get the stored Virtual NFC ID
        val virtualNfcId = nfcManager.getVirtualNfcId()
        
        return if (virtualNfcId != null) {
            // Send the Virtual NFC ID to the gate reader
            virtualNfcId.toByteArray(Charsets.UTF_8)
        } else {
            // No ID registered yet
            "NOT_REGISTERED".toByteArray(Charsets.UTF_8)
        }
    }
    
    override fun onDeactivated(reason: Int) {
        Log.d("GemHCE", "HCE deactivated: $reason")
    }
}
```

---

### 5. **User Login/Registration Flow**

Implement this **SIMPLIFIED** flow in your login/registration activity:

```kotlin
class LoginActivity : AppCompatActivity() {
    
    private lateinit var nfcManager: NFCManager
    private val viewModelScope = CoroutineScope(Dispatchers.Main + Job())
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        nfcManager = NFCManager(this)
    }
    
    private fun onLoginOrRegister(email: String, name: String?) {
        viewModelScope.launch {
            try {
                showLoading("Logging in...")
                
                // Generate or get existing Virtual NFC ID
                val virtualNfcId = nfcManager.getOrCreateVirtualNfcId(0) // userId not needed yet
                
                // Single API call handles everything!
                val result = nfcManager.loginOrRegister(
                    email = email,
                    name = name,
                    virtualNfcId = virtualNfcId
                )
                
                if (result.isSuccess) {
                    val response = result.getOrNull()!!
                    val user = response.user
                    
                    if (response.is_new_user) {
                        showToast("Welcome ${user.name}! Account created ✓")
                    } else {
                        showToast("Welcome back ${user.name}!")
                    }
                    
                    hideLoading()
                    navigateToMainScreen(user.id, user.name ?: user.email)
                } else {
                    hideLoading()
                    showError("Login failed: ${result.exceptionOrNull()?.message}")
                }
                
            } catch (e: Exception) {
                hideLoading()
                showError("Error: ${e.message}")
            }
        }
    }
}
```

### OLD FLOW (Don't use this anymore)
<details>
<summary>Click to see the old two-step flow (deprecated)</summary>

```kotlin
class LoginActivity : AppCompatActivity() {
    
    private lateinit var nfcManager: NFCManager
    private lateinit var apiService: GemApiService
    private val viewModelScope = CoroutineScope(Dispatchers.Main + Job())
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        nfcManager = NFCManager(this)
        apiService = RetrofitClient.gemApiService
    }
    
    private fun onLoginSuccess(userId: Int, email: String) {
        viewModelScope.launch {
            try {
                // Step 1: Register Virtual NFC ID with backend
                if (!nfcManager.isRegistered()) {
                    showLoading("Setting up NFC access...")
                    
                    val result = nfcManager.registerWithBackend(userId)
                    
                    if (result.isSuccess) {
                        val response = result.getOrNull()
                        Log.d("NFC", "Registered: ${response?.virtual_nfc_id}")
                        showToast("NFC access enabled ✓")
                    } else {
                        Log.e("NFC", "Registration failed", result.exceptionOrNull())
                        showToast("Warning: NFC registration failed")
                    }
                    
                    hideLoading()
                }
                
                // Step 2: Navigate to main app
                navigateToMainScreen(userId)
                
            } catch (e: Exception) {
                Log.e("Login", "Error in post-login setup", e)
                hideLoading()
            }
        }
    }
    
    private fun onRegisterNewUser(email: String, name: String) {
        viewModelScope.launch {
            try {
                showLoading("Creating account...")
                
                // Step 1: Create visitor in backend
                val createRequest = CreateVisitorRequest(
                    email = email,
                    name = name,
                    gender = null
                )
                
                val response = apiService.createVisitor(createRequest)
                
                if (response.isSuccessful && response.body() != null) {
                    val visitor = response.body()!!
                    
                    // Step 2: Register NFC
                    val nfcResult = nfcManager.registerWithBackend(visitor.id)
                    
                    if (nfcResult.isSuccess) {
                        showToast("Account created with NFC access ✓")
                    }
                    
                    hideLoading()
                    navigateToMainScreen(visitor.id)
                } else {
                    hideLoading()
                    showError("Registration failed: ${response.code()}")
                }
                
            } catch (e: Exception) {
                hideLoading()
                showError("Error: ${e.message}")
            }
        }
    }
}
```
</details>

---

### 6. **Optional: Link Physical Card Feature**

If users can link physical souvenir cards from the app:

```kotlin
class ProfileActivity : AppCompatActivity() {
    
    private lateinit var apiService: GemApiService
    
    fun onLinkPhysicalCard(userId: Int, cardUid: String) {
        lifecycleScope.launch {
            try {
                showLoading("Linking card...")
                
                val request = LinkCardRequest(
                    user_id = userId,
                    card_uid = cardUid
                )
                
                val response = apiService.linkPhysicalCard(request)
                
                if (response.isSuccessful && response.body() != null) {
                    val result = response.body()!!
                    showToast(result.message)
                } else if (response.code() == 400) {
                    showError("Card already linked to another user")
                } else {
                    showError("Failed to link card: ${response.code()}")
                }
                
                hideLoading()
                
            } catch (e: Exception) {
                hideLoading()
                showError("Error: ${e.message}")
            }
        }
    }
}
```

---

### 7. **Testing & Debugging**

Add these debug features:

```kotlin
class DebugNFCActivity : AppCompatActivity() {
    
    private lateinit var nfcManager: NFCManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        nfcManager = NFCManager(this)
        
        // Display current NFC status
        findViewById<TextView>(R.id.tvNfcId).text = 
            "Virtual NFC ID: ${nfcManager.getVirtualNfcId() ?: "Not generated"}"
        
        findViewById<TextView>(R.id.tvRegistered).text = 
            "Registered: ${nfcManager.isRegistered()}"
        
        // Test NFC reader simulation
        findViewById<Button>(R.id.btnTestScan).setOnClickListener {
            testGateScan()
        }
        
        // Clear NFC data (for testing)
        findViewById<Button>(R.id.btnClearNFC).setOnClickListener {
            nfcManager.clearNfcData()
            recreate()
        }
    }
    
    private fun testGateScan() {
        val virtualNfcId = nfcManager.getVirtualNfcId()
        if (virtualNfcId == null) {
            showToast("No NFC ID generated yet")
            return
        }
        
        lifecycleScope.launch {
            try {
                val request = GateScanRequest(scanned_id = virtualNfcId)
                val response = RetrofitClient.gemApiService.scanAtGate(request)
                
                if (response.isSuccessful && response.body() != null) {
                    val result = response.body()!!
                    
                    if (result.status == "ACCESS_GRANTED") {
                        showToast("✅ ${result.welcome_message}")
                    } else {
                        showToast("❌ Access Denied")
                    }
                }
            } catch (e: Exception) {
                showError("Test failed: ${e.message}")
            }
        }
    }
}
```

---

### 8. **Retrofit Setup**

Create your Retrofit client:

```kotlin
object RetrofitClient {
    
    private const val BASE_URL = "http://YOUR_SERVER_IP:8000/"
    
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()
    
    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    val gemApiService: GemApiService = retrofit.create(GemApiService::class.java)
}
```

---

### 9. **Dependencies (build.gradle.kts)**

```kotlin
dependencies {
    // Retrofit
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.11.0")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.2")
    
    // ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.6.2")
    
    // NFC (included in Android SDK, no additional dependency needed)
}
```

---

## Summary

**Key Points:**
1. ✅ Generate `virtual_nfc_id` on first launch/login
2. ✅ Store it permanently in SharedPreferences
3. ✅ **Use single endpoint `POST /api/auth/login-register`** - handles everything!
4. ✅ Implement HCE service to broadcast the ID
5. ✅ ID is **fixed forever** - never regenerated
6. ✅ Use the same ID for all future gate entries

**PRIMARY API Endpoint:**
- `POST /api/auth/login-register` - **ONE CALL** for login/register + NFC registration

**Optional Endpoints:**
- `POST /api/cards/link` - Link physical card (optional feature)
- `POST /api/gate/scan` - Test gate authentication (for debugging)
- `GET /visitors/` - List visitors (admin feature)

**Backend Base URL:**
```
http://YOUR_SERVER_IP:8000/
```

Replace `YOUR_SERVER_IP` with your actual server IP address (e.g., `192.168.1.100` for local network or your cloud server IP).
