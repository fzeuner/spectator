from scipy.io import readsav
import numpy as np


class datReader:
    """
    Reader for .dat (IDL .sav) files with robust state harmonization.

    Behavior:
    - Accepts state arrays that may be 2D (H, W) or 3D (K, H, W).
    - For 3D arrays, averages along the smallest dimension to obtain a 2D (H, W).
      Example: (2, 560, 1260) -> average over axis 0 -> (560, 1260).
    - After reducing to 2D candidates, selects the majority common shape and drops
      states that do not match that shape (e.g., tiny 2x2 placeholders).
    - Exposes processed images and state names consistently.
    """

    def __init__(self, path: str = "", python_dict: bool = True, verbose: bool = False):
        self.path = path
        self.verbose = verbose
        self.python_dict = python_dict
        # Raw dict as read from file (may contain extra fields like 'info')
        self.dat = readsav(self.path, None, self.python_dict, None, self.verbose)

        # Processed outputs (computed lazily)
        self._processed = False
        self._images_2d: list[np.ndarray] = []
        self._state_names: list[str] = []
        self._info = None

    def _ensure_processed(self):
        if self._processed:
            return

        # Extract info section if present
        try:
            self._info = self.dat.get('info') if hasattr(self.dat, 'get') else self.dat['info']
        except Exception:
            self._info = None

        # Collect candidate arrays per state key (exclude 'info')
        candidates: list[tuple[str, np.ndarray]] = []
        try:
            # readsav result behaves like dict; iterate keys
            for key in self.dat:
                if key == 'info':
                    continue
                arr = self.dat[key]
                if isinstance(arr, np.ndarray):
                    candidates.append((key, arr))
        except Exception:
            # If iteration fails, fall back to attributes access is not supported; leave empty
            candidates = []

        # Reduce each candidate to a 2D array, choosing the axis with the smallest size when reduction is needed
        reduced: list[tuple[str, np.ndarray]] = []
        shape_votes: dict[tuple[int, int], int] = {}

        for name, arr in candidates:
            try:
                if arr.ndim == 2:
                    reduced_arr = arr
                elif arr.ndim >= 3:
                    # Choose axis with smallest size to average over
                    axis = int(np.argmin(arr.shape))
                    reduced_arr = arr.mean(axis=axis)
                    # If still >2D (e.g., averaged axis in middle), keep averaging singleton axes if any
                    while reduced_arr.ndim > 2:
                        # Prefer averaging over any axis with size 1 first, otherwise the smallest
                        sizes = reduced_arr.shape
                        if 1 in sizes:
                            axis2 = int(list(sizes).index(1))
                        else:
                            axis2 = int(np.argmin(sizes))
                        reduced_arr = reduced_arr.mean(axis=axis2)
                else:
                    # 1D or others are not usable for images
                    continue

                # Ensure 2D
                if reduced_arr.ndim != 2:
                    continue

                shape = (int(reduced_arr.shape[0]), int(reduced_arr.shape[1]))
                shape_votes[shape] = shape_votes.get(shape, 0) + 1
                reduced.append((name, np.asarray(reduced_arr)))
            except Exception:
                continue

        # Choose majority shape (highest vote). If tie, choose the one with largest area.
        target_shape: tuple[int, int] | None = None
        if shape_votes:
            # Sort by (count desc, area desc)
            target_shape = sorted(shape_votes.items(), key=lambda kv: (kv[1], kv[0][0] * kv[0][1]), reverse=True)[0][0]

        images_2d: list[np.ndarray] = []
        state_names: list[str] = []
        if target_shape is not None:
            for name, arr2d in reduced:
                if tuple(arr2d.shape) == target_shape:
                    state_names.append(name)
                    images_2d.append(arr2d)

        # Persist results
        self._images_2d = images_2d
        self._state_names = state_names
        self._processed = True

    def getDat(self):
        """Return a processed dict with harmonized states and preserved 'info'."""
        self._ensure_processed()
        out = {}
        if self._info is not None:
            out['info'] = self._info
        for name, img in zip(self._state_names, self._images_2d):
            out[name] = img
        return out
    
    def getDatInfo(self):
        self._ensure_processed()
        return self._info
    
    def getDatImagesArray(self):
        """Return list of 2D images for the selected states (majority shape)."""
        self._ensure_processed()
        return list(self._images_2d)