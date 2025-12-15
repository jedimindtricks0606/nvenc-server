import React, { useEffect } from 'react';
import { FileText } from 'lucide-react';

interface OutputFilenameInputProps {
  file: File | null;
  outputFilename: string;
  onOutputFilenameChange: (filename: string) => void;
}

const OutputFilenameInput: React.FC<OutputFilenameInputProps> = ({
  file,
  outputFilename,
  onOutputFilenameChange
}) => {
  useEffect(() => {
    if (file && !outputFilename) {
      const baseName = file.name.replace(/\.[^/.]+$/, '');
      onOutputFilenameChange(`${baseName}_processed.mp4`);
    }
  }, [file, outputFilename, onOutputFilenameChange]);

  return (
    <div className="w-full">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        输出文件名
      </label>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <FileText className="h-4 w-4 text-gray-400" />
        </div>
        <input
          type="text"
          value={outputFilename}
          onChange={(e) => onOutputFilenameChange(e.target.value)}
          placeholder="输入输出文件名..."
          className="w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">
        默认基于输入文件生成，可自定义修改
      </p>
    </div>
  );
};

export default OutputFilenameInput;