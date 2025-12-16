import React, { useState } from 'react';
import { Video, Settings } from 'lucide-react';
import FileUpload from './components/FileUpload';
import CommandInput from './components/CommandInput';
import OutputFilenameInput from './components/OutputFilenameInput';
import ProcessControl from './components/ProcessControl';
import ResultDisplay from './components/ResultDisplay';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [command, setCommand] = useState('');
  const [outputFilename, setOutputFilename] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<{
    status?: 'success' | 'error' | 'info';
    message?: string;
    downloadUrl?: string;
  }>({});

  const canProcess = file && command && outputFilename;

  const handleProcess = async () => {
    if (!file || !command || !outputFilename) return;

    setIsProcessing(true);
    setResult({ status: 'info', message: '正在上传文件...' });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('command', command);
    formData.append('output_filename', outputFilename);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
          'X-Command': command,
        },
        body: formData,
      });

      const contentType = response.headers.get('content-type') || '';
      let data: any = {};
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        try { data = JSON.parse(text); } catch { data = { message: text }; }
      }

      if (response.ok && (data.download_url || data.download_path)) {
        const url = data.download_url || (data.download_path ? `/api${data.download_path}` : undefined);
        const ms = typeof data.duration_ms === 'number' ? data.duration_ms : undefined;
        const secText = ms !== undefined ? `耗时 ${(ms / 1000).toFixed(2)}s` : '';
        setResult({
          status: 'success',
          message: secText ? `视频处理完成！${secText}` : '视频处理完成！',
          downloadUrl: url,
        });
      } else {
        setResult({
          status: 'error',
          message: (data.message && typeof data.duration_ms === 'number' ? `${data.message}，耗时 ${(data.duration_ms / 1000).toFixed(2)}s` : data.message) || data.error || `处理失败 (HTTP ${response.status})`,
        });
      }
    } catch (error) {
      setResult({
        status: 'error',
        message: '网络错误，请确保后端服务已启动',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (result.downloadUrl) {
      window.open(result.downloadUrl, '_blank');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <Video className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold text-gray-900">视频处理工具</h1>
          </div>
          <p className="text-gray-600">上传视频文件，输入 FFmpeg 命令进行处理</p>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-lg shadow-lg p-6 space-y-6">
          {/* File Upload */}
          <FileUpload file={file} onFileChange={setFile} />

          {/* Command Input */}
          <CommandInput command={command} onCommandChange={setCommand} />

          {/* Output Filename */}
          <OutputFilenameInput
            file={file}
            outputFilename={outputFilename}
            onOutputFilenameChange={setOutputFilename}
          />

          {/* Process Control */}
          <ProcessControl
            isProcessing={isProcessing}
            canProcess={!!canProcess}
            downloadUrl={result.downloadUrl}
            onProcess={handleProcess}
            onDownload={handleDownload}
          />

          {/* Result Display */}
          {result.message && (
            <ResultDisplay
              status={result.status}
              message={result.message}
              downloadUrl={result.downloadUrl}
              onDownload={handleDownload}
            />
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-500 text-sm">
          <div className="flex items-center justify-center space-x-2">
            <Settings className="h-4 w-4" />
            <span>基于 FFmpeg 的强大视频处理能力</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
