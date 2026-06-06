from vieneu import Vieneu

# Initialize in Standard mode (Default - Highest quality)
tts = Vieneu(emotion="natural") # emotion="natural" (giọng tự nhiên - mặc định) hoặc "storytelling" (giọng kể chuyện)
danh_sach_doc = tts.list_preset_voices
# 1. Simple synthesis (uses default Northern Female voice 'Trúc Ly')
text = "Chào bạn. Tôi là VieNeu-TTS, tôi có thể giúp bạn đọc sách, làm chatbot thời gian thực, thậm chí clone giọng nói của bạn."
audio = tts.infer(text=text)

# Save to file
tts.save(audio, "output_Trúc Ly.wav")
print("💾 Saved to output_Trúc Ly.wav")

# 2. Using a specific Preset Voice
voices = tts.list_preset_voices()
for desc, voice_id in voices:
    print(f"Voice: {desc} (ID: {voice_id})")

my_voice_id = voices[1][1] if len(voices) > 1 else voices[0][1] # Giọng Phạm Tuyên
voice_data = tts.get_preset_voice(my_voice_id)

audio_custom = tts.infer(text="Tôi đang nói bằng giọng của Bác sĩ Tuyên.", voice=voice_data)

# 3. Save to file
tts.save(audio_custom, "output_Phạm Tuyên.wav")
print("💾 Saved to output_Phạm Tuyên.wav")
