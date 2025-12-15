import React from 'react';
import { Code, Terminal } from 'lucide-react';

interface CommandInputProps {
  command: string;
  onCommandChange: (command: string) => void;
}

const CommandInput: React.FC<CommandInputProps> = ({ command, onCommandChange }) => {
  const commonCommands = [
    {
      name: 'H.264 编码',
      command: 'ffmpeg -y -i {input} -c:v libx264 -b:v 4M -c:a aac {output}'
    },
    {
      name: 'H.265 编码',
      command: 'ffmpeg -y -i {input} -c:v libx265 -b:v 4M -c:a aac {output}'
    },
    {
      name: 'NVENC H.264',
      command: 'ffmpeg -y -i {input} -c:v h264_nvenc -b:v 4M -c:a aac {output}'
    },
    {
      name: 'NVENC H.265',
      command: 'ffmpeg -y -i {input} -c:v hevc_nvenc -b:v 4M -c:a aac {output}'
    },
    {
      name: '压缩视频',
      command: 'ffmpeg -y -i {input} -c:v libx264 -crf 23 -c:a aac {output}'
    },
    {
      name: '提取音频',
      command: 'ffmpeg -y -i {input} -vn -acodec copy {output}'
    },
    {
      name: '转码为MP4',
      command: 'ffmpeg -y -i {input} -c copy {output}'
    }
  ];

  const handleCommandSelect = (selectedCommand: string) => {
    onCommandChange(selectedCommand);
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-gray-700">
          FFmpeg 命令
        </label>
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-gray-400" />
          <span className="text-xs text-gray-500">确保包含 {'{input}'} 和 {'{output}'} 占位符</span>
        </div>
      </div>
      
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {commonCommands.map((cmd, index) => (
            <button
              key={index}
              onClick={() => handleCommandSelect(cmd.command)}
              className="px-3 py-1 text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
            >
              {cmd.name}
            </button>
          ))}
        </div>
        
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Code className="h-4 w-4 text-gray-400" />
          </div>
          <textarea
            value={command}
            onChange={(e) => onCommandChange(e.target.value)}
            placeholder="输入 FFmpeg 命令..."
            className="w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            rows={3}
          />
        </div>
        
        <div className="text-xs text-gray-500">
          <p>提示：命令中必须包含 <code className="bg-gray-100 px-1 rounded">{'{input}'}</code> 和 <code className="bg-gray-100 px-1 rounded">{'{output}'}</code> 占位符</p>
        </div>
      </div>
    </div>
  );
};

export default CommandInput;