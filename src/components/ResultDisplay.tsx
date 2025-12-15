import React from 'react';
import { CheckCircle, XCircle, AlertCircle, Download } from 'lucide-react';

interface ResultDisplayProps {
  status?: 'success' | 'error' | 'info';
  message?: string;
  downloadUrl?: string;
  onDownload: () => void;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({
  status,
  message,
  downloadUrl,
  onDownload
}) => {
  if (!status && !message) {
    return null;
  }

  const getIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'info':
      default:
        return <AlertCircle className="h-5 w-5 text-blue-500" />;
    }
  };

  const getBgColor = () => {
    switch (status) {
      case 'success':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'error':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200 text-blue-800';
    }
  };

  return (
    <div className={`border rounded-lg p-4 ${getBgColor()}`}>
      <div className="flex items-start space-x-3">
        {getIcon()}
        <div className="flex-1">
          <p className="text-sm font-medium">{message}</p>
          
          {downloadUrl && status === 'success' && (
            <div className="mt-3">
              <button
                onClick={onDownload}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors"
              >
                <Download className="h-4 w-4" />
                <span>下载处理后的文件</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResultDisplay;