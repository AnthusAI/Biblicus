import { Panel, Group, Separator } from 'react-resizable-panels';

export function TestResizable() {
  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <Group direction="horizontal">
        <Panel defaultSize={30} minSize={20}>
          <div style={{ background: 'lightblue', height: '100%', padding: '20px' }}>
            <h2>Left Panel</h2>
            <p>This should be resizable</p>
          </div>
        </Panel>
        <Separator style={{ width: '4px', background: '#ccc', cursor: 'col-resize' }} />
        <Panel defaultSize={70} minSize={20}>
          <div style={{ background: 'lightgreen', height: '100%', padding: '20px' }}>
            <h2>Right Panel</h2>
            <p>Drag the gray bar to resize</p>
          </div>
        </Panel>
      </Group>
    </div>
  );
}
