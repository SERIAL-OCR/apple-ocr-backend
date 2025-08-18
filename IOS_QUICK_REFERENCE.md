# 📱 iOS Quick Reference - Apple OCR Backend

## ⚡ **Essential Information**

### **Base URL**
```swift
let baseURL = "http://localhost:8000"  // Development
```

### **Critical Field Name**
```swift
// ✅ REQUIRED - Use "image" field name
formData.append(imageData, withName: "image")  // NOT "file"
```

## 🔧 **Quick Integration**

### **1. Submit Scan Request**
```swift
POST /scan
Content-Type: multipart/form-data

Fields:
- image: [image file] (REQUIRED)
- device_type: "iphone" (OPTIONAL)
```

### **2. Check Job Status**
```swift
GET /result/{job_id}
```

### **3. Health Check**
```swift
GET /health
```

## 🚨 **Most Common Issues**

### **Issue 1: "Field required" Error**
```swift
// ❌ WRONG
formData.append(imageData, withName: "file")

// ✅ CORRECT  
formData.append(imageData, withName: "image")
```

### **Issue 2: Server Not Responding**
```bash
# Check if server is running
curl http://localhost:8000/health
```

### **Issue 3: Processing Timeout**
```swift
// Increase polling attempts
let maxAttempts = 120 // 10 minutes
```

## 📊 **Expected Performance**

- **Fast**: 4-8 seconds (60-70%)
- **Average**: 8-12 seconds  
- **Slow**: 30-60 seconds
- **Detection Rate**: 85-90%

## 🎯 **Quick Test**

```swift
// Test with curl
curl -X POST "http://localhost:8000/scan" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@test_image.jpg" \
  -F "device_type=iphone"
```

## 📚 **Full Documentation**

- **Complete Guide**: [IOS_INTEGRATION_GUIDE.md](IOS_INTEGRATION_GUIDE.md)
- **API Reference**: [README.md](README.md)

---

**Key Point**: Always use `"image"` as the field name, not `"file"`! 🎯
