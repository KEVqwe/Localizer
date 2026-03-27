import React, { useState } from 'react';

export const ValidationForm = ({
  taskId,
  initialSubtitles,
  initialUiElements,
  onApprove
}: any) => {
  const [subtitles, setSubtitles] = useState(initialSubtitles || []);
  const [uiElements, setUiElements] = useState(initialUiElements || []);

  const handleSubmit = () => {
    onApprove(taskId, {
      validated_subtitles: subtitles,
      validated_ui_elements: uiElements
    });
  };

  return (
    <div className="p-4 bg-white rounded shadow">
      <h2 className="text-xl font-bold mb-4">Validate Extraction (Task {taskId})</h2>
      
      <div className="mb-4">
        <h3 className="font-semibold text-lg">Subtitles</h3>
        <textarea 
          className="w-full h-32 p-2 border" 
          value={JSON.stringify(subtitles, null, 2)}
          onChange={(e) => setSubtitles(JSON.parse(e.target.value))}
        />
      </div>

      <div className="mb-4">
        <h3 className="font-semibold text-lg">UI Elements</h3>
        <textarea 
          className="w-full h-32 p-2 border" 
          value={JSON.stringify(uiElements, null, 2)}
          onChange={(e) => setUiElements(JSON.parse(e.target.value))}
        />
      </div>

      <button 
        onClick={handleSubmit}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Approve & Translate
      </button>
    </div>
  );
};
