from krita import DockWidgetFactory, DockWidgetFactoryBase
from .krita_flash import DockerTemplate

DOCKER_ID = 'krita_flash'
instance = Krita.instance()
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
                                        DockWidgetFactoryBase.DockRight,
                                        DockerTemplate)

instance.addDockWidgetFactory(dock_widget_factory)