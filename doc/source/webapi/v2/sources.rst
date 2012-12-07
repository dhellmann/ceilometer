=========
 Sources
=========

.. http:get:: /v2/sources

   Retrieve source definitions for all identity sources.

.. http:get:: /v2/sources/(source_id)

   Retrieve a single identity source definition.

   :param source_id: The unique identifier for the source.
   :statuscode 200: no error
   :statuscode 404: no such source
   :returns: Details of the source. :wsme:type:`Source`

.. autotype:: ceilometer.api.controllers.v2.Source
   :members:
