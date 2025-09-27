# 🎤 Testing the Voice Recognition Feature

## How to Test the Microphone Button

### Step 1: Open the Application
1. Open `index.html` in your browser (Chrome recommended)
2. You should see the microphone button (🎤) next to the search input field

### Step 2: Verify Button Visibility
- The microphone button should be visible as a 🎤 icon
- It should be positioned right next to the search input field
- When you hover over it, it should change color slightly

### Step 3: Test Voice Recognition
1. **Click the microphone button** - it should turn red (🔴) when recording
2. **Say a phrase** like:
   - "Delhi to Dubai"
   - "Los Angeles to New York"  
   - "London to Paris"
3. **Watch for results**:
   - The button should return to normal (🎤) after you stop speaking
   - The search input should populate with ICAO codes (e.g., "VIDP,OMDB")
   - The weather search should start automatically

### Step 4: Check Status Messages
- Look for status messages near the microphone button showing:
  - "Voice input ready"
  - "Listening..." (when recording)
  - "Heard: [your speech]"
  - "Converted to: [ICAO codes]"

## Troubleshooting

### If you don't see the microphone button:
1. Check browser console (F12) for errors
2. Try refreshing the page
3. Make sure you're using Chrome, Edge, or Safari

### If the button doesn't work:
1. **Browser Compatibility**: Speech recognition works best in Chrome
2. **HTTPS Required**: Some browsers require HTTPS for microphone access
3. **Permissions**: Allow microphone access when prompted

### If voice recognition fails:
1. Check microphone permissions in browser settings
2. Speak clearly and not too fast
3. Try supported phrases like "Delhi to Dubai"
4. Check browser console for detailed error messages

## Supported Speech Patterns

| What to Say | Expected Result |
|-------------|----------------|
| "Delhi to Dubai" | VIDP,OMDB |
| "Los Angeles to New York" | KLAX,KJFK |
| "London to Paris" | EGLL,LFPG |
| "Mumbai to Singapore" | VABB,WSSS |
| "Tokyo to Seoul" | RJTT,RKSI |
| "Sydney to Auckland" | YSSY,NZAA |

## Debug Testing

### Use the Test Page
1. Open `mic_test.html` for isolated testing
2. This page will show detailed debug information
3. Click "Run All Tests" to verify functionality

### Browser Console
1. Press F12 to open developer tools
2. Watch the console for messages like:
   - "Voice recording started"
   - "Speech recognition result: [text]"
   - "Voice recording ended"

### Network Requirements
- The main application requires backend API access
- The microphone functionality works offline
- Airport name conversion works entirely client-side

## Expected Behavior

### Successful Voice Input Flow:
1. Click 🎤 → Button turns red 🔴
2. Speak "Delhi to Dubai"
3. Status shows "Heard: delhi to dubai"
4. Status shows "Converted to: VIDP,OMDB. Searching..."
5. Search input populates with "VIDP,OMDB"
6. Weather analysis starts automatically

### Visual Feedback:
- **Normal State**: Gray 🎤 button
- **Recording State**: Red 🔴 button with pulse animation  
- **Success State**: Green status message
- **Error State**: Red error popup message

## Browser Support

| Browser | Voice Recognition | Microphone Button |
|---------|-------------------|-------------------|
| Chrome | ✅ Full Support | ✅ Works |
| Edge | ✅ Full Support | ✅ Works |
| Firefox | ❌ Not Supported | ✅ Visible (non-functional) |
| Safari | ✅ Limited Support | ✅ Works (iOS/macOS) |

## Common Issues & Solutions

### Issue: Microphone button not visible
**Solution**: Check CSS conflicts, try hard refresh (Ctrl+F5)

### Issue: "Speech recognition not supported"
**Solution**: Use Chrome or Edge browser

### Issue: "Microphone permission denied"
**Solution**: 
1. Click the microphone icon in the address bar
2. Allow microphone access
3. Refresh the page

### Issue: Voice not converting to airports
**Solution**: 
1. Speak clearly and slowly
2. Use supported airport names
3. Follow pattern: "[Airport 1] to [Airport 2]"

### Issue: Search doesn't start automatically
**Solution**: Check browser console for JavaScript errors

If you're still having issues, check the browser console (F12) for detailed error messages.