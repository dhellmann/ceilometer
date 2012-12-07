========
 Meters
========

.. default-domain:: wsme

.. root:: ceilometer.api.controllers.root.RootController

Listing Meters
==============

.. http:get:: /v2/meters

.. autotype:: ceilometer.api.controllers.v2.MeterDescription
   :members:

.. autotype:: ceilometer.api.controllers.v2.Meter
   :members:

Listing Data
============

.. autotype:: ceilometer.api.controllers.v2.Event
   :members:

Computing Stats for Meters
==========================

.. autotype:: ceilometer.api.controllers.v2.MeterVolume
   :members:

.. autotype:: ceilometer.api.controllers.v2.Duration
   :members:
