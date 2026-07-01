import warnings
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
import torch

warnings.filterwarnings("ignore", message="cannot import name '_C' from 'sam2'")
warnings.filterwarnings("ignore", message="Skipping the post-processing step")


def _has_cuda() -> bool:
    return torch.cuda.is_available()


def _get_device() -> torch.device:
    return torch.device("cuda" if _has_cuda() else "cpu")


def _has_ort_gpu() -> bool:
    try:
        import onnxruntime as ort
        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


def _to_tensor(image: Image.Image, device: torch.device | None = None) -> torch.Tensor:
    arr = np.array(image).astype(np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return t.to(device or _get_device())


def _from_tensor(t: torch.Tensor) -> Image.Image:
    arr = (t.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    if arr.shape[2] == 1:
        arr = arr.repeat(3, axis=2)
    return Image.fromarray(arr)


class ImageEditor:
    SUPPORTED_FORMATS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    @staticmethod
    def load(path: str | Path) -> Image.Image:
        return Image.open(path).convert("RGBA")

    _sam2_generator = None

    @staticmethod
    def _get_sam2():
        if ImageEditor._sam2_generator is None:
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            from sam2.build_sam import build_sam2
            from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
            model = build_sam2("sam2_hiera_t.yaml", None, device=_get_device())
            ImageEditor._sam2_generator = SAM2AutomaticMaskGenerator(
                model,
                points_per_side=32,
                points_per_batch=32,
                pred_iou_thresh=0.5,
                stability_score_thresh=0.5,
                stability_score_offset=0.5,
                box_nms_thresh=0.5,
                crop_nms_thresh=0.5,
                min_mask_region_area=100,
            )
        return ImageEditor._sam2_generator

    @staticmethod
    def remove_background_sam2(image: Image.Image) -> Image.Image:
        generator = ImageEditor._get_sam2()
        img_rgb = image.convert("RGB")
        img_np = np.array(img_rgb)
        total_pixels = img_np.shape[0] * img_np.shape[1]
        masks = generator.generate(img_np)
        if not masks:
            return image.convert("RGBA")
        filtered = [m for m in masks if m["area"] < total_pixels * 0.95]
        if not filtered:
            filtered = masks
        best = max(filtered, key=lambda m: m["area"] * m.get("stability_score", 0))
        mask = Image.fromarray(best["segmentation"].astype(np.uint8) * 255)
        fg = image.convert("RGBA")
        r, g, b, a = fg.split()
        a = ImageOps.fit(mask, a.size, Image.NEAREST)
        return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def remove_background(image: Image.Image, model_name: str = "u2net") -> Image.Image:
        import onnxruntime as ort
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        try:
            session = ort.InferenceSession(
                model_name, providers=providers,
                provider_options=[{"device_id": 0}, {}]
            )
        except Exception:
            session = None
        from rembg import remove as rembg_remove, new_session
        if session is None:
            session = new_session(model_name)
            result = rembg_remove(np.array(image), session=session)
        else:
            result = rembg_remove(np.array(image), session=session)
        return Image.fromarray(result).convert("RGBA")

    @staticmethod
    def replace_bg_image(image: Image.Image, bg_image: Image.Image) -> Image.Image:
        fg = image.convert("RGBA")
        bg = bg_image.convert("RGBA").resize(fg.size, Image.LANCZOS)
        bg.paste(fg, (0, 0), fg)
        return bg.convert("RGB")

    @staticmethod
    def save(image: Image.Image, path: str | Path, quality: int = 95) -> Path:
        path = Path(path)
        ext = path.suffix.lower()
        if ext == ".png":
            image.save(path, format="PNG")
        elif ext in (".jpg", ".jpeg"):
            image.save(path, format="JPEG", quality=quality)
        elif ext == ".webp":
            image.save(path, format="WEBP", quality=quality)
        else:
            image.save(path)
        return path

    # ── GPU-accelerated enhancements ──────────────────────────────

    @staticmethod
    def upscale(image: Image.Image, scale: float = 2.0) -> Image.Image:
        device = _get_device()
        has_alpha = image.mode == "RGBA"
        rgb = image.convert("RGB")
        t = _to_tensor(rgb, device)
        _, _, h, w = t.shape
        nh, nw = int(h * scale), int(w * scale)
        t_up = torch.nn.functional.interpolate(t, size=(nh, nw), mode="bicubic", align_corners=False)
        result = _from_tensor(t_up)
        if has_alpha:
            alpha = image.split()[-1]
            alpha = alpha.resize((nw, nh), Image.LANCZOS)
            result.putalpha(alpha)
        return result

    @staticmethod
    def adjust_sharpness(image: Image.Image, factor: float = 1.5) -> Image.Image:
        device = _get_device()
        has_alpha = image.mode == "RGBA"
        rgb = image.convert("RGB")
        t = _to_tensor(rgb, device)
        blurred = torch.nn.functional.avg_pool2d(t, kernel_size=3, stride=1, padding=1)
        t = torch.clamp(t + (t - blurred) * (factor - 1.0), 0.0, 1.0)
        result = _from_tensor(t)
        if has_alpha:
            result.putalpha(image.split()[-1])
        return result

    @staticmethod
    def denoise(image: Image.Image, strength: float = 0.1) -> Image.Image:
        device = _get_device()
        has_alpha = image.mode == "RGBA"
        rgb = image.convert("RGB")
        t = _to_tensor(rgb, device)
        kernel = torch.tensor([[[[1, 2, 1], [2, 4, 2], [1, 2, 1]]]], dtype=torch.float32, device=device) / 16.0
        kernel = kernel.expand(3, 1, 3, 3)
        blurred = torch.nn.functional.conv2d(t, kernel, padding=1, groups=3)
        t = torch.clamp(t + (blurred - t) * (1.0 - strength), 0.0, 1.0)
        result = _from_tensor(t)
        if has_alpha:
            result.putalpha(image.split()[-1])
        return result

    @staticmethod
    def cleanup():
        import gc as _gc
        if ImageEditor._sam2_generator is not None:
            gen = ImageEditor._sam2_generator
            ImageEditor._sam2_generator = None
            del predictor
            _gc.collect()
            if _has_cuda():
                torch.cuda.empty_cache()
        _gc.collect()
        try:
            import onnxruntime as ort
            ort._get_default_session_options()
        except Exception:
            pass

    @staticmethod
    def gpu_info() -> str:
        if _has_cuda():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            return f"GPU (PyTorch): {name} ({vram:.1f} GB)"
        if _has_ort_gpu():
            import onnxruntime as ort
            return f"GPU (ONNX): {ort.get_device()}"
        return "Không có GPU"
