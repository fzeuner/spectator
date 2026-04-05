"""
Unit tests for PlotDataModel and AxisConfig.
"""

import numpy as np
import pytest
from spectator.models import PlotDataModel, AxisConfig, AxisConfigs


class TestAxisConfig:
    """Tests for AxisConfig class."""
    
    def test_spatial_window_config(self):
        """Test spatial window configuration."""
        config = AxisConfigs.spatial_window()
        assert config.x_label == "z"
        assert config.y_label == "x"
        assert config.line_angle == 0
        assert config.swap_plot_coords is True
    
    def test_spectrum_window_config(self):
        """Test spectrum window configuration."""
        config = AxisConfigs.spectrum_window()
        assert config.x_label == "λ"
        assert config.y_label == "z"
        assert config.line_angle == 90
        assert config.swap_plot_coords is False
    
    def test_get_plot_coordinates_spatial(self):
        """Test coordinate transformation for spatial window."""
        config = AxisConfigs.spatial_window()
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        indices = (np.arange(10), np.arange(5))
        
        x, y = config.get_plot_coordinates(data, indices)
        
        # For spatial window: x=data, y=indices (swapped)
        np.testing.assert_array_equal(x, data)
        np.testing.assert_array_equal(y, np.arange(5))
    
    def test_get_plot_coordinates_spectrum(self):
        """Test coordinate transformation for spectrum window."""
        config = AxisConfigs.spectrum_window()
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        indices = (np.arange(5), np.arange(10))
        
        x, y = config.get_plot_coordinates(data, indices)
        
        # For spectrum window: x=indices, y=data (not swapped)
        np.testing.assert_array_equal(x, np.arange(5))
        np.testing.assert_array_equal(y, data)
    
    def test_invalid_axis_source(self):
        """Test that invalid axis source raises error."""
        with pytest.raises(ValueError):
            AxisConfig(
                x_axis_source='invalid',
                y_axis_source='data'
            )


class TestPlotDataModel:
    """Tests for PlotDataModel class."""
    
    def test_init_2d_data(self):
        """Test initialization with 2D data."""
        data = np.random.rand(100, 50)
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        assert model.shape == (100, 50)
        assert model.ndim == 2
        assert model.data is data
    
    def test_get_slice_at_index(self):
        """Test slicing along a dimension."""
        data = np.arange(60).reshape(10, 6)
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        # Slice along dimension 0 at index 5
        slice_data = model.get_slice_at_index(0, 5)
        expected = data[5, :]
        
        np.testing.assert_array_equal(slice_data, expected)
    
    def test_get_averaged_slice(self):
        """Test averaged slicing."""
        data = np.arange(60).reshape(10, 6)
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        # Average along dimension 0 from index 2 to 4
        avg_slice = model.get_averaged_slice(0, 2, 4)
        expected = data[2:5, :].mean(axis=0)
        
        np.testing.assert_array_equal(avg_slice, expected)
    
    def test_get_averaged_slice_reversed_indices(self):
        """Test that reversed start/end indices are handled correctly."""
        data = np.arange(60).reshape(10, 6)
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        # Should work the same regardless of order
        avg1 = model.get_averaged_slice(0, 2, 4)
        avg2 = model.get_averaged_slice(0, 4, 2)
        
        np.testing.assert_array_equal(avg1, avg2)
    
    def test_validate_index(self):
        """Test index validation and clamping."""
        data = np.zeros((10, 6))
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        # Valid index
        assert model.validate_index(0, 5) == 5
        
        # Out of bounds - should clamp
        assert model.validate_index(0, -1) == 0
        assert model.validate_index(0, 100) == 9
        assert model.validate_index(1, 10) == 5
    
    def test_get_plot_data_spatial(self):
        """Test getting plot coordinates for spatial window."""
        data = np.arange(60).reshape(10, 6)
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        # Get a slice
        slice_data = model.get_slice_at_index(0, 3)
        
        # Convert to plot coordinates
        x, y = model.get_plot_data(slice_data)
        
        # For spatial window: x=data values, y=spatial indices
        np.testing.assert_array_equal(x, data[3, :])
        np.testing.assert_array_equal(y, np.arange(6))
    
    def test_get_plot_data_spectrum(self):
        """Test getting plot coordinates for spectrum window."""
        data = np.arange(60).reshape(10, 6)
        config = AxisConfigs.spectrum_window()
        model = PlotDataModel(data, config)
        
        # Get a slice along spatial dimension
        slice_data = model.get_slice_at_index(1, 2)
        
        # Convert to plot coordinates
        x, y = model.get_plot_data(slice_data)
        
        # For spectrum window: x=spectral indices, y=data values
        np.testing.assert_array_equal(x, np.arange(10))
        np.testing.assert_array_equal(y, data[:, 2])
    
    def test_update_data(self):
        """Test updating data."""
        data1 = np.zeros((10, 6))
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data1, config)
        
        # Update with new data of same shape
        data2 = np.ones((15, 8))
        model.update_data(data2)
        
        assert model.shape == (15, 8)
        np.testing.assert_array_equal(model.data, data2)
    
    def test_update_data_wrong_dimensions(self):
        """Test that updating with wrong dimensionality raises error."""
        data1 = np.zeros((10, 6))
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data1, config)
        
        # Try to update with 3D data
        data2 = np.ones((5, 10, 6))
        
        with pytest.raises(ValueError):
            model.update_data(data2)
    
    def test_get_dimension_size(self):
        """Test getting dimension sizes."""
        data = np.zeros((10, 6))
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        assert model.get_dimension_size(0) == 10
        assert model.get_dimension_size(1) == 6
    
    def test_get_index_array(self):
        """Test getting index arrays."""
        data = np.zeros((10, 6))
        config = AxisConfigs.spatial_window()
        model = PlotDataModel(data, config)
        
        np.testing.assert_array_equal(model.get_index_array(0), np.arange(10))
        np.testing.assert_array_equal(model.get_index_array(1), np.arange(6))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
