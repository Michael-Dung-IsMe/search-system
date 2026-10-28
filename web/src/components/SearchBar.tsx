'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Camera, Mic, Search } from 'lucide-react';

const VOICE_RECORDING_SECONDS = 20;

interface SearchBarProps {
  value: string;
  onChange: (val: string) => void;
  onSearch: (text: string) => void;
  onImageSelected: (file: File) => void;
  onVoiceRecorded: (blob: Blob) => Promise<void> | void;
  isProcessing?: boolean;
  placeholder?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  onSearch,
  onImageSelected,
  onVoiceRecorded,
  isProcessing = false,
  placeholder = 'Mô tả phong cách, tải ảnh outfit hoặc nói yêu cầu...',
}) => {
  const [isListening, setIsListening] = useState(false);
  const [countdown, setCountdown] = useState(VOICE_RECORDING_SECONDS);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const countdownTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Stop recording cleanup
  const stopRecording = () => {
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsListening(false);
  };

  // Start recording with a 20-second countdown
  const startRecording = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Trình duyệt không hỗ trợ Web Audio API để ghi âm.');
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        stream.getTracks().forEach((track) => track.stop());
        await onVoiceRecorded(audioBlob);
      };

      recorder.start();
      setIsListening(true);
      setCountdown(VOICE_RECORDING_SECONDS);

      let timeLeft = VOICE_RECORDING_SECONDS;
      countdownTimerRef.current = setInterval(() => {
        timeLeft -= 1;
        setCountdown(timeLeft);
        if (timeLeft <= 0) {
          stopRecording();
        }
      }, 1000);
    } catch (err) {
      console.error('Không thể kích hoạt microphone:', err);
      alert('Không thể truy cập Microphone. Vui lòng cấp quyền trong trình duyệt.');
      setIsListening(false);
    }
  };

  const handleVoiceToggle = () => {
    if (isListening) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImageSelected(file);
      // Reset input value so re-selecting same file triggers change
      e.target.value = '';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSearch(value);
    }
  };

  useEffect(() => {
    return () => {
      if (countdownTimerRef.current) {
        clearInterval(countdownTimerRef.current);
      }
    };
  }, []);

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col gap-2.5">
      <div
        className={`relative flex items-center bg-white border rounded-2xl px-3.5 py-2 transition-all duration-300 ${
          isProcessing
            ? 'border-indigo-500 shadow-[0_0_0_3px_rgba(99,102,241,0.18),0_0_25px_rgba(99,102,241,0.3)] animate-pulse'
            : 'border-gray-200 hover:border-gray-300 focus-within:border-gray-900 focus-within:shadow-md'
        }`}
      >
        <input
          type="text"
          className="flex-1 bg-transparent border-none outline-none text-gray-900 text-base placeholder-gray-400 py-1.5 pl-2"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        <div className="flex items-center gap-1.5">
          {/* Voice Search Button */}
          <button
            type="button"
            onClick={handleVoiceToggle}
            title={isListening ? 'Bấm để dừng ghi âm' : 'Tìm bằng giọng nói (20s tự ngắt)'}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              isListening
                ? 'bg-red-50 text-red-600 border border-red-300 animate-bounce'
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Mic size={20} />
          </button>

          {/* Camera Upload Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Tải ảnh outfit lên để tìm kiếm"
            className="w-10 h-10 rounded-xl flex items-center justify-center text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-all"
          >
            <Camera size={20} />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
          />

          {/* Search Submit Button */}
          <button
            type="button"
            onClick={() => onSearch(value)}
            className="bg-gray-900 hover:bg-gray-800 text-white font-medium text-sm px-4 py-2 rounded-xl flex items-center gap-1.5 transition-all active:scale-95"
          >
            <Search size={16} />
            <span className="hidden sm:inline">Tìm kiếm</span>
          </button>
        </div>
      </div>

      {/* Voice Status Bar with 20-second countdown */}
      {isListening && (
        <div className="flex items-center justify-between px-4 py-2 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs sm:text-sm animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
            <span>Đang lắng nghe giọng nói của bạn... Hãy nói yêu cầu tìm kiếm</span>
          </div>
          <span className="font-bold tabular-nums text-red-800 bg-red-100 px-2 py-0.5 rounded-md">
            {countdown}s
          </span>
        </div>
      )}
    </div>
  );
};
