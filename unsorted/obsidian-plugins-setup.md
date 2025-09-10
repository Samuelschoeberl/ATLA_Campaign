# Obsidian Plugins Setup for Developers & Data Scientists

This guide covers the installation and basic setup of the **best Obsidian plugins** for code, data workflows, dashboards, and research.

---

## 1. Install Plugins
1. Open **Settings → Community Plugins**.
2. Enable **Safe Mode** if it's disabled.
3. Click **Browse**.
4. Search and install the following plugins:
   - Dataview
   - Templater
   - QuickAdd
   - RunJS
   - Note Toolbar
   - Better Search Views
   - Obsidian Tags Overview

---

## 2. Plugin Configuration

### **Dataview**
- Go to **Settings → Dataview**.
- Enable **JavaScript Queries** for dynamic calculations.
- Example query to list all datasets:
    ```dataview
    TABLE file.name, size, date
    FROM "datasets"
    SORT date DESC
    ```

---

### **Templater**
- Set **Template Folder Location**: `templates/`
- Create a file `dataset-template.md`:
    ```markdown
    # {{title}}
    **Date:** <% tp.date.now("YYYY-MM-DD") %>
    **Source:** <% tp.file.cursor() %>
    ```

---

### **QuickAdd**
- Create a new **Capture Command** → “New Dataset”
- Use the `dataset-template.md` to quickly add new entries.

---

### **RunJS**
- Go to **Settings → RunJS**.
- Add a snippet:
    ```js
    const data = [1,2,3,4];
    return data.map(x => x * 2);
    ```
- Run inline JS inside notes with `==js` blocks.

---

### **Note Toolbar**
- Add quick buttons for:
    - “New Dataset”
    - “Run Dataview Query”
    - “Open Dashboard”

---

### **Better Search Views**
- Use advanced search like:
    ```
    tag:#dataset size:>10MB
    ```

---

### **Obsidian Tags Overview**
- Go to the **Tags Overview** pane to visualize tags as a dataset tree.

---

## 3. Recommended Folder Structure
```plaintext
📂 vault/
 ├── datasets/
 │   ├── dataset1.md
 │   ├── dataset2.md
 ├── dashboards/
 │   ├── main-dashboard.md
 ├── templates/
 │   ├── dataset-template.md
 ├── scripts/
 │   ├── data-cleaning.js
```

---

## 4. Next Steps
- Combine **Dataview** + **Templater** to generate **automatic dashboards**.
- Use **RunJS** for inline computations and plotting.
- Tag datasets with `#raw`, `#processed`, and `#visualized` for powerful filtering.

---
**Pro Tip:**  
Use [Obsidian Git](https://github.com/denolehov/obsidian-git) to version-control datasets and scripts.
