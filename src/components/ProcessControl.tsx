import React from 'react';
import { Play, Loader2, Download } from 'lucide-react';

interface ProcessControlProps {
  isProcessing: boolean;
  canProcess: boolean;
  downloadUrl?: string;
  onProcess: () => void;
  onDownload: () => void;
}

const ProcessControl: React.FC<ProcessControlProps> = ({
  isProcessing,
  canProcess,
  downloadUrl,
  onProcess,
  onDownload
}) => {
  return (
    <div className="w-full space-y-4">
      <div className="flex space-x-4">
        <button
          onClick={onProcess}
          disabled={!canProcess || isProcessing}
          className={`flex-1 flex items-center justify-center space-x-2 py-3 px-6 rounded-lg font-medium transition-colors ${
            !canProcess || isProcessing
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>处理中...</span>
            </>
          ) : (
            <>
              <Play className="h-5 w-5" />
              <span>开始处理</span>
            </>
          )}
        </button>

        {downloadUrl && (
          <button
            onClick={onDownload}
            className="flex items-center justify-center space-x-2 py-3 px-6 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
          >
            <Download className="h-5 w-5" />
            <span>下载文件</span>
          </button>
        )}
      </div>

      {isProcessing && (
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '100%' }}></div>
        </div>
      )}
    </div>
  );
};

export default ProcessControl;