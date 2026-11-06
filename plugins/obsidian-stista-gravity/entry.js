const { Plugin, ItemView, Notice } = require('obsidian');
const { render } = require('./graph-view.js');
const TYPE = 'stista-gravity-view';

class GravityView extends ItemView {
  getViewType() {
    return TYPE;
  }
  getDisplayText() {
    return 'Tongue Gravity';
  }
  getIcon() {
    return 'compass';
  }
  async onOpen() {
    if (this.dispose) this.dispose();
    this.contentEl.empty();
    try {
      const graph = JSON.parse(
        await this.app.vault.adapter.read('.obsidian/plugins/stista-gravity/graph.json')
      );
      this.dispose = render(this.contentEl, graph, async (path) => {
        const file = this.app.vault.getAbstractFileByPath(path);
        if (file && file.extension === 'md') await this.app.workspace.getLeaf('tab').openFile(file);
        else new Notice('This note has moved. Refresh the Tongue Atlas index.');
      });
    } catch (error) {
      this.contentEl.createEl('p', {
        text: 'The local Tongue Atlas index could not be opened: ' + error.message,
      });
    }
  }
  async onClose() {
    if (this.dispose) this.dispose();
  }
}

module.exports = class GravityPlugin extends Plugin {
  async onload() {
    this.registerView(TYPE, (leaf) => new GravityView(leaf));
    const open = async () => {
      let leaf = this.app.workspace.getLeavesOfType(TYPE)[0];
      if (!leaf) {
        leaf = this.app.workspace.getLeaf('tab');
        await leaf.setViewState({ type: TYPE, active: true });
      }
      await this.app.workspace.revealLeaf(leaf);
    };
    this.addRibbonIcon('compass', 'Open Tongue Gravity', open);
    this.addCommand({ id: 'open-gravity', name: 'Open Tongue Gravity', callback: open });
    this.addCommand({
      id: 'reload-gravity',
      name: 'Reload Tongue Gravity data',
      callback: async () => {
        const leaves = this.app.workspace.getLeavesOfType(TYPE);
        if (!leaves.length) return open();
        for (const leaf of leaves) await leaf.view.onOpen();
      },
    });
  }
};
